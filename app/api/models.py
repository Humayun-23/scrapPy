from typing import Optional

from pydantic import BaseModel


class ScrapeRequest(BaseModel):
    url: str
    wait_for: Optional[str] = None
    extract_json: Optional[bool] = False
    screenshot: Optional[bool] = False
    timeout: Optional[int] = 30


class ActionStep(BaseModel):
    action: str
    selector: Optional[str] = None
    value: Optional[str] = None
    text: Optional[str] = None
    wait_ms: Optional[int] = None
    timeout_ms: Optional[int] = None
    delay_ms: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None


class BrowserRequest(BaseModel):
    url: str
    steps: Optional[list[ActionStep]] = None
    wait_for: Optional[str] = None
    extract_json: Optional[bool] = False
    screenshot: Optional[bool] = False
    timeout: Optional[int] = 30


class BatchRequest(BaseModel):
    urls: list[str]
    wait_for: Optional[str] = None
    timeout: Optional[int] = 30


class ProxyRequest(BaseModel):
    region: Optional[str] = "us"


class KeyCreateRequest(BaseModel):
    email: str
    plan: Optional[str] = "free"


class CheckoutRequest(BaseModel):
    email: str
    plan: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
