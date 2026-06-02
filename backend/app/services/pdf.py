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

    # Ensure cache dir exists and is writable before Tectonic tries to create it.
    os.makedirs(_CACHE_DIR, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        pdf_path = os.path.join(tmpdir, "resume.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_content)

        env = {
            **os.environ,
            # appuser is created with --no-create-home so $HOME is /nonexistent.
            # Tectonic falls back to $HOME/.cache when XDG vars are unset, which
            # causes EPERM. Override both so all writes land in /tmp.
            "HOME": "/tmp",
            "XDG_CACHE_HOME": "/tmp/.cache",
            "TECTONIC_CACHE_DIR": _CACHE_DIR,
            # Suppress interactive prompts in the TeX engine
            "TEXMFHOME": tmpdir,
        }

        proc = await asyncio.create_subprocess_exec(
            "tectonic",
            "--cache-dir", _CACHE_DIR,  # explicit CLI arg, not just env var
            tex_path,
            cwd=tmpdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            _stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=180.0,  # generous for first-run package downloads
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("LaTeX compilation timed out (180 s)")

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"LaTeX compilation failed:\n{err[:800]}")

        if not os.path.exists(pdf_path):
            raise RuntimeError("Tectonic exited successfully but no PDF was produced")

        with open(pdf_path, "rb") as f:
            return f.read()
