import subprocess
import cv2
import numpy as np
import yt_dlp

# 取得直播串流真實 URL
def get_stream_url(youtube_url):
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=False)
        formats = info_dict.get('formats', [info_dict])
        best = max(formats, key=lambda f: f.get('height', 0))
        return best['url']

# 啟動 ffmpeg 串流輸出為 rawvideo pipe
def open_ffmpeg_stream(stream_url, width=1280, height=720):
    command = [
        'ffmpeg',
        '-i', stream_url,
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f'{width}x{height}',
        '-'
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10**8)

# 圖片貼上（支援透明度）
def overlay_image(base_frame, overlay_img, position='bottom_left'):
    h, w, _ = base_frame.shape
    oh, ow, _ = overlay_img.shape

    if position == 'bottom_left':
        x, y = 0, h - oh
    elif position == 'bottom_right':
        x, y = w - ow, h - oh
    else:
        raise ValueError("目前僅支援 bottom_left/bottom_right")

    roi = base_frame[y:y+oh, x:x+ow]

    if overlay_img.shape[2] == 4:
        alpha = overlay_img[..., 3:] / 255.0
        overlay_rgb = overlay_img[..., :3]
        roi[:] = (1 - alpha) * roi + alpha * overlay_rgb
    else:
        roi[:] = overlay_img

    return base_frame

def main():
    # 修改這邊為你想看的直播連結
    youtube_url = "youtube_url"
    # 這是一個範例連結
    # youtube_url = "https://www.youtube.com/watch?v=xwAWSh35uuw"
    stream_url = get_stream_url(youtube_url)

    # 調整解析度需與 ffmpeg -s 一致
    width, height = 1280, 720
    frame_size = width * height * 3

    process = open_ffmpeg_stream(stream_url, width, height)

    # 載入你要疊加的圖片
    overlay_img = cv2.imread("overlay.png", cv2.IMREAD_UNCHANGED)
    if overlay_img is None:
        raise ValueError("無法讀取圖片，請確認 your_overlay.png 存在")

    # 可選擇 resize overlay 符合直播尺寸
    max_width = int(width * 0.25)
    if overlay_img.shape[1] > max_width:
        scale = max_width / overlay_img.shape[1]
        overlay_img = cv2.resize(overlay_img, (0, 0), fx=scale, fy=scale)

    print("🚀 開始直播串流處理...")
    while True:
        raw_frame = process.stdout.read(frame_size)
        if not raw_frame:
            break

        # 加上 .copy() 解決 read-only 問題
        frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3)).copy()

        frame = overlay_image(frame, overlay_img, position='bottom_left')

        cv2.imshow("📺 Live Stream Overlay", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    process.stdout.close()
    process.wait()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
