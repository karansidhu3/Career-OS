from pydantic import BaseModel, EmailStr


class WaitlistSignup(BaseModel):
    email: EmailStr


class WaitlistSignupResponse(BaseModel):
    status: str
