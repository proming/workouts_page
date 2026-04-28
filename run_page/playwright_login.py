import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

_DIR = Path(__file__).parent

app = FastAPI(title="Garmin Login Service")

class LoginRequest(BaseModel):
    user: str
    is_cn: bool = True

def _do_login(user: str, is_cn: bool) -> str:
    domain = "garmin.cn" if is_cn else "garmin.com"
    sso = f"https://sso.{domain}/sso"
    sso_embed = f"{sso}/embed"
    signin_url = f"{sso}/signin?" + urlencode({
        "id": "gauth-widget",
        "embedWidget": "true",
        "gauthHost": sso,
        "service": sso_embed,
        "source": sso_embed,
        "redirectAfterAccountLoginUrl": sso_embed,
        "redirectAfterAccountCreationUrl": sso_embed,
    })

    creds_file = _DIR / f"credentials-{user}.json"
    if not creds_file.exists():
        raise RuntimeError(f"Credentials file {creds_file} not found")

    try:
        creds = json.loads(creds_file.read_text())
    except Exception as e:
        raise RuntimeError(f"Failed to read or parse credentials JSON: {e}")

    try:
        with sync_playwright() as p:
            # 在服务端运行建议开启headless=True，如果Garmin登录遇到验证码可以改为False并在本地登录一次
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )).new_page()

            page.goto(signin_url)
            page.wait_for_load_state("networkidle")
            page.fill('input[name="username"]', creds["username"])
            page.fill('input[name="password"]', creds["password"])
            page.click("#login-btn-signin")

            try:
                page.wait_for_url("**/embed?ticket=**", timeout=60_000)
            except Exception as e:
                # 超时往往意味着密码错误或者遭遇滑块验证码
                raise RuntimeError(f"Login timeout or blocked (e.g., incorrect password or captcha). Current URL: {page.url}") from e

            ticket_url = page.url
            browser.close()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Playwright browser automation failed: {e}") from e

    m = re.search(r'[?&]ticket=(ST-[^&\s]+)', ticket_url)
    if not m:
        raise RuntimeError(f"No CAS ticket found in URL: {ticket_url}")
    ticket = m.group(1)

    try:
        from garth.http import Client
        from garth.sso import exchange, get_oauth1_token
        client = Client()
        client.configure(domain=domain, ssl_verify=False)
        oauth1 = get_oauth1_token(ticket, client)
        oauth2 = exchange(oauth1, client)
        client.configure(oauth1_token=oauth1, oauth2_token=oauth2)
        # client.dump(str(tokenstore))
        # print(f"Tokens saved to {tokenstore}/")
        return client.dumps()
    except Exception as e:
        raise RuntimeError(f"Garth token exchange failed: {e}") from e

@app.post("/login")
def api_login(request: LoginRequest):
    try:
        secret = _do_login(request.user, request.is_cn)
        return {"status": "success", "secret_string": secret}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
