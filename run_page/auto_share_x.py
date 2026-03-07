import argparse
import datetime

import tweepy
import os

import utils
from config import SQL_FILE
from generator import Generator

# --- 1. 获取你的Twitter API凭据 ---
# 强烈建议使用环境变量来存储，避免硬编码！
CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# 检查凭据是否存在
if not all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
    print("错误：请设置所有Twitter API环境变量（TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET）")
    print("你可以通过'export VAR_NAME=VALUE'（Linux/macOS）或'$env:VAR_NAME=VALUE' (Windows PowerShell) 来设置。")
    exit()

def send_x(tweet_text, tweet_image):
    try:
      # --- 2. 准备上传图片和发布推文的API客户端 ---
      # tweepy.API (用于v1.1 API, 例如媒体上传)
      # tweepy.Client (用于v2 API, 例如发布推文)

      # 创建v1.1 API的认证对象（主要用于媒体上传，因为v1.1的媒体上传更稳定且功能完善）
      auth = tweepy.OAuth1UserHandler(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
      api_v1 = tweepy.API(auth)

      # 创建v2 API的客户端对象（用于发布推文）
      # Client可以使用OAuth1凭据进行用户上下文操作
      client_v2 = tweepy.Client(
          consumer_key=CONSUMER_KEY,
          consumer_secret=CONSUMER_SECRET,
          access_token=ACCESS_TOKEN,
          access_token_secret=ACCESS_TOKEN_SECRET
      )
      if not os.path.exists(tweet_image):
          print(f"错误：图片文件 '{tweet_image}' 不存在。请确保路径正确。")
          exit()

      # --- 4. 上传图片 ---
      print(f"正在上传图片: {tweet_image}...")
      media_upload_response = api_v1.media_upload(tweet_image)
      # media_upload_response.media_id_string 包含了上传图片后X返回的媒体ID
      media_id = media_upload_response.media_id_string
      print(f"图片上传成功，Media ID: {media_id}")

      # --- 5. 发布带图片和文本的推文 ---
      print(f"正在发布推文: '{tweet_text}' 并关联图片 ID: {media_id}...")

      # 使用client_v2对象的create_tweet方法发布推文
      # media_ids 参数接受一个包含一个或多个媒体ID的列表
      response = client_v2.create_tweet(text=tweet_text, media_ids=[media_id])

      # --- 6. 处理发布结果 ---
      if response.data:
          tweet_id = response.data['id']
          tweet_url = f"https://x.com/user/status/{tweet_id}"  # 注意，这里的user需要是你的twitter用户名，或者直接用twitter.com
          print("\n推文发布成功！")
          print(f"推文ID: {tweet_id}")
          print(f"推文内容: {response.data['text']}")
          print(f"查看推文: {tweet_url}")
      else:
          print("\n错误：发布推文失败，未收到有效数据。")
          if response.errors:
              print("API错误信息:")
              for error in response.errors:
                  print(error)

    except tweepy.TweepyException as e:
      print(f"Tweepy API 错误: {e}")
      if hasattr(e, 'response') and e.response:
          print(f"Error Code: {e.response.status_code}")
          print(f"Error Message: {e.response.text}")
    except Exception as e:
      print(f"发生未知错误: {e}")

    # 上传生成临时图片
    os.remove(tweet_image)

def run_auto_sync(date):
    generator = Generator(SQL_FILE)
    generator.only_run = True
    activities_list = generator.load()
    if date:
        activity = next(
            (
                activity
                for activity in activities_list
                if activity["start_date_local"].startswith(date)
            ),
            None,
        )
        if not activity:
            print(f"No activity found for date: {date}")
            return
    else:
        activity = activities_list[-1]

    activity_date = activity.get("start_date_local", "").split()[0]
    if activity_date != date and datetime.date.today().strftime('%Y-%m-%d') != activity_date:
        exit()

    tweet_text = ""
    tweet_image = ""
    if "summary_polyline" in activity and activity["summary_polyline"]:
        year = activity.get("start_date_local", "")[:4]
        directory = os.path.join(f"{args.blog_dir}/../../../assets", f"run_{year}")
        file_name = activity_date.replace('-', '') + "_" + str(activity.get("run_id",""))

        from cairosvg import svg2png
        svg2png(url=os.path.join(directory, f"{file_name}.svg"),
                 write_to=os.path.join(directory, f"{file_name}.png"))
        tweet_image = os.path.join(directory, f"{file_name}.png")

        tweet_text += f"时间： {activity.get('start_date_local', '')}  \n"
        tweet_text += f"距离： {activity.get('distance', 0) / 1000:.2f} km  \n"
        tweet_text += f"时长： {activity.get('moving_time', '').split('.')[0]}  \n"
        tweet_text += f"配速： {utils.speed_to_pace(activity.get('average_speed', 0) * 3.6)}  \n"
        tweet_text += f"心率： {int(activity.get('average_heartrate', 0))} bpm"
    else:
        print("No route data found")

    send_x(tweet_text, tweet_image)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate route visualization")
    parser.add_argument("--date", help="Date of the activity in YYYY-MM-DD format")
    parser.add_argument(
        "--blog-dir",
        dest="blog_dir",
        metavar="DIR",
        type=str,
        default=".",
        help="Directory containing blog files (default: current directory).",
    )
    args = parser.parse_args()
    run_auto_sync(date=args.date)
