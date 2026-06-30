"""Server-side LaTeX → PDF compilation via Tectonic."""

import asyncio
import os
import tempfile


# Shared cache dir so package downloads persist across requests on the same container.
_CACHE_DIR = "/tmp/tectonic-cache"


async def compile_latex_to_pdf(latex_content: str) -> bytes:
    """
    Compile a LaTeX string to PDF using Tectonic.

    First call on a cold container will download required TeX packages (~100–200 MB,
    30–90 s). Subsequent calls reuse the cache and take ~5–15 s.

    Raises RuntimeError on compilation failure or FileNotFoundError if tectonic
    is not installed (local dev without tectonic in PATH).
    """
    # Tectonic (XeTeX engine) doesn't need the [pdftex] hyperref driver option.
    # Remove it so the document compiles cleanly under XeTeX.
    latex_content = latex_content.replace("[pdftex]{hyperref}", "{hyperref}")
    # fontawesome5 crashes Tectonic on macOS (SIGABRT). fontawesome (v4) is
    # compatible and uses identical icon command names (\faEnvelope etc).
    latex_content = latex_content.replace("{fontawesome5}", "{fontawesome}")

    # Ensure cache dir exists and is writable before Tectonic tries to create it.
    os.makedirs(_CACHE_DIR, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        pdf_path = os.path.join(tmpdir, "resume.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_content)

        # Build a minimal environment for Tectonic — never inherit application
        # secrets (ANTHROPIC_API_KEY, DATABASE_URL, API_KEY, etc.).
        # CONTAINER=1 is set in the Dockerfile; locally it's unset.
        in_container = os.environ.get("CONTAINER") == "1"
        _safe_keys = {"PATH", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP"}
        env = {k: v for k, v in os.environ.items() if k in _safe_keys}
        env["TECTONIC_CACHE_DIR"] = _CACHE_DIR
        env["TEXMFHOME"] = tmpdir
        if in_container:
            env.update({
                "HOME": "/tmp",
                "XDG_CACHE_HOME": "/tmp/.cache",
            })
        else:
            home = os.path.expanduser("~")
            if home:
                env["HOME"] = home

        proc = await asyncio.create_subprocess_exec(
            "tectonic",
            tex_path,
            cwd=tmpdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=180.0,  # generous for first-run package downloads
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("LaTeX compilation timed out (180 s)")

        if proc.returncode != 0:
            # Tectonic writes errors to stdout; stderr is usually empty.
            err = (stdout + stderr).decode("utf-8", errors="replace")
            raise RuntimeError(f"LaTeX compilation failed:\n{err[:800]}")

        if not os.path.exists(pdf_path):
            raise RuntimeError("Tectonic exited successfully but no PDF was produced")

        with open(pdf_path, "rb") as f:
            return f.read()
