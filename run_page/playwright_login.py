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
        import urllib.request
        import urllib.parse
        import json
        import os

        bot_token = os.getenv("TG_BOT_TOKEN")
        chat_id = os.getenv("TG_CHAT_ID")
        thread_id = os.getenv("TG_MESSAGE_THREAD_ID")
        # Telegram Bot API URL
        url = f"https://api.telegram.org/{bot_token}/sendMessage"

        # 准备请求数据（对应 curl 中的 -d 参数）
        data = {
            "chat_id": chat_id,
            "text": str(e),
            "message_thread_id": thread_id
        }

        # 使用 urllib.parse.urlencode 将字典转换为 URL 编码的字符串，并编码为 utf-8 字节流
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')

        # 创建 Request 对象，传入 data 参数会自动将其转换为 POST 请求
        req = urllib.request.Request(url, data=data_encoded)

        try:
            # 发送请求并读取响应
            with urllib.request.urlopen(req) as response:
                response_body = response.read().decode('utf-8')

                # 将返回的 JSON 字符串解析为 Python 字典并格式化打印
                result = json.loads(response_body)
                print("消息发送成功！返回结果：")
                print(json.dumps(result, indent=4, ensure_ascii=False))

        except urllib.error.URLError as e1:
            print(f"请求失败: {e1}")
        except Exception as e2:
            print(f"发生错误: {e2}")

        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
