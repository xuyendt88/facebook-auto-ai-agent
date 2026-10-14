import os
import time
import requests
import urllib.parse
from google import genai

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")
SOURCE_PAGE_URL = "https://www.facebook.com/IEEvietnam"

client = genai.Client(api_key=GEMINI_API_KEY)

def fetch_latest_facebook_post():
    print(f"Đang cào bài viết mới từ nguồn: {SOURCE_PAGE_URL}...")
    url = f"https://api.apify.com/v2/acts/apify~facebook-posts-scraper/runs?token={APIFY_API_TOKEN}"
    payload = {
        "startUrls": [{"url": SOURCE_PAGE_URL}],
        "resultsLimit": 1
    }
    response = requests.post(url, json=payload)
    if response.status_code != 201:
        raise Exception(f"Lỗi gọi Apify: {response.text}")
    
    run_data = response.json()["data"]
    dataset_id = run_data["defaultDatasetId"]
    
    time.sleep(30)
    
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}"
    items_res = requests.get(dataset_url)
    posts = items_res.json()
    
    if posts and len(posts) > 0:
        return posts[0].get("text", "") or posts[0].get("caption", "")
    return None

def rewrite_content(original_text):
    print("Đang dùng Google Gemini viết lại văn phong mới...")
    
    iee_footer = """----------------------------------
IEE – Tư vấn du học Toàn quốc
Địa chỉ: số 27 ngõ 23 Đỗ Quang, Yên Hoà, Hà Nội
Hotline: 0969.159.131
Đăng ký tư vấn Miễn phí: https://forms.gle/MuTGJFbU99rNVbyw6"""

    system_instruction = f"Bạn là chuyên gia truyền thông và sáng tạo nội dung cho trung tâm tư vấn du học IEE. Hãy đọc bài viết gốc, giữ nguyên các thông tin chính thống, số liệu hoặc kiến thức hữu ích về du học, nhưng hãy viết lại hoàn toàn văn phong sao cho mới mẻ, thu hút và cuốn hút hơn. Tuyệt đối loại bỏ mọi số điện thoại hoặc thông tin liên hệ cũ của bài gốc (nếu có). Ở PHẦN CUỐI CÙNG của bài viết, bạn BẮT BUỘC phải giữ nguyên và chèn chính xác đoạn thông tin sau:\n\n{iee_footer}"

    # Sử dụng model gemini-1.5-flash với cơ chế chờ nếu gặp quá tải tạm thời
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{system_instruction}\n\nBài viết gốc:\n{original_text}"
            )
            return response.text
        except Exception as e:
            print(f"Lần thử {attempt + 1} gặp lỗi: {e}. Đang chờ 5 giây để gọi lại...")
            time.sleep(5)
    raise Exception("Không thể gọi Gemini sau 3 lần thử.")

def generate_ai_image(post_content):
    print("Đang tạo câu lệnh (prompt) vẽ ảnh bằng Gemini...")
    prompt_res = client.models.generate_content(
        model='gemini-1.5-flash',
        contents="Dựa vào nội dung bài viết dưới đây, hãy viết một câu lệnh ngắn gọn (prompt) bằng tiếng Англійська (English) để tạo ra một bức ảnh minh họa chuyên nghiệp, phong cách chụp ảnh chân thực (photorealistic), phù hợp cho bài đăng tư vấn du học. Chỉ trả về câu lệnh bằng tiếng Anh, không kèm giải thích.\n\n" + post_content
    )
    image_prompt = prompt_res.text.strip()
    print(f"Prompt tạo ảnh: {image_prompt}")

    encoded_prompt = urllib.parse.quote(image_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    print(f"Tạo ảnh miễn phí thành công: {image_url}")
    return image_url

def post_to_facebook(message, image_url):
    print("Đang đăng bài kèm ảnh lên Fanpage...")
    url = f"https://graph.facebook.com/v18.0/{FACEBOOK_PAGE_ID}/photos"
    payload = {
        "url": image_url,
        "caption": message,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Đăng bài thành công lên Fanpage!")
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
