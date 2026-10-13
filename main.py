import os
import time
import requests
from openai import OpenAI

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
# Cố định nguồn cào chính xác từ Page IEEvietnam
SOURCE_PAGE_URL = "https://www.facebook.com/IEEvietnam"

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_latest_facebook_post():
    print(f"Đang cào bài viết mới từ nguồn: {SOURCE_PAGE_URL}...")
    url = f"https://api.apify.com/v2/acts/apify~facebook-page-scraper/runs?token={APIFY_API_TOKEN}"
    payload = {
        "startUrls": [{"url": SOURCE_PAGE_URL}],
        "maxPosts": 1
    }
    response = requests.post(url, json=payload)
    if response.status_code != 201:
        raise Exception(f"Lỗi gọi Apify: {response.text}")
    
    run_data = response.json()["data"]
    dataset_id = run_data["defaultDatasetId"]
    
    # Chờ Apify hoàn tất quá trình cào dữ liệu
    time.sleep(30)
    
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}"
    items_res = requests.get(dataset_url)
    posts = items_res.json()
    
    if posts and len(posts) > 0:
        return posts[0].get("text", "")
    return None

def rewrite_content(original_text):
    print("Đang dùng AI nhào lặn, viết lại văn phong mới và chuẩn hóa thông tin liên hệ...")
    
    iee_footer = """----------------------------------
IEE – Tư vấn du học Toàn quốc
Địa chỉ: số 27 ngõ 23 Đỗ Quang, Yên Hoà, Hà Nội
Hotline: 0969.159.131
Đăng ký tư vấn Miễn phí: https://forms.gle/MuTGJFbU99rNVbyw6"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"Bạn là chuyên gia truyền thông và sáng tạo nội dung cho trung tâm tư vấn du học IEE. Hãy đọc bài viết gốc, giữ nguyên các thông tin chính thống, số liệu hoặc kiến thức hữu ích về du học, nhưng hãy viết lại hoàn toàn văn phong sao cho mới mẻ, thu hút và cuốn hút hơn. Tuyệt đối loại bỏ mọi số điện thoại hoặc thông tin liên hệ cũ của bài gốc (nếu có). Ở PHẦN CUỐI CÙNG của bài viết, bạn BẮT BUỘC phải giữ nguyên và chèn chính xác đoạn thông tin sau:\n\n{iee_footer}"
            },
            {
                "role": "user",
                "content": original_text
            }
        ]
    )
    return response.choices[0].message.content

def generate_ai_image(post_content):
    print("Đang yêu cầu AI sáng tạo câu lệnh (prompt) để vẽ ảnh minh họa mới...")
    prompt_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Dựa vào nội dung bài viết dưới đây, hãy viết một câu lệnh (prompt) bằng tiếng Anh để tạo ra một bức ảnh minh họa chuyên nghiệp, có người thật, phong cách chụp ảnh chân thực (photorealistic), phù hợp cho bài đăng tư vấn du học. Chỉ trả về câu lệnh bằng tiếng Anh, không kèm giải thích."
            },
            {
                "role": "user",
                "content": post_content
            }
        ]
    )
    image_prompt = prompt_res.choices[0].message.content
    print(f"Prompt tạo ảnh: {image_prompt}")

    image_response = client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = image_response.data[0].url
    print(f"Tạo ảnh thành công: {image_url}")
    return image_url

def post_to_facebook(message, image_url):
    print("Đang đăng bài kèm ảnh mới lên Fanpage của bạn...")
    url = f"https://graph.facebook.com/v18.0/{FACEBOOK_PAGE_ID}/photos"
    payload = {
        "url": image_url,
        "caption": message,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Đăng bài kèm ảnh AI thành công lên Fanpage!")
    else:
        print(f"Lỗi đăng bài Facebook: {response.text}")

if __name__ == "__main__":
    post_text = fetch_latest_facebook_post()
    if post_text:
        new_content = rewrite_content(post_text)
        new_image_url = generate_ai_image(new_content)
        post_to_facebook(new_content, new_image_url)
    else:
        print("Không tìm thấy bài viết mới nào từ nguồn.")
