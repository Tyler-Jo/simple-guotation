import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import cv2
import numpy as np
import pytesseract
from deep_translator import GoogleTranslator
from PIL import ImageFont, ImageDraw, Image
import time
import os

# 페이지 설정
st.set_page_config(page_title="실시간 중한 번역기", layout="wide")
st.title("📸 실시간 중국어 -> 한국어 번역기 (Light)")

# 같은 폴더에 있는 폰트 파일명
FONT_PATH = "NanumGothic.ttf"

class VideoProcessor:
    def __init__(self):
        self.translator = GoogleTranslator(source='zh-CN', target='ko')
        self.last_results = []       
        self.last_process_time = 0   
        self.process_interval = 1.5  # 1.5초마다 번역 수행 (랙 방지)

        # 로컬 폰트 로드
        if os.path.exists(FONT_PATH):
            self.font = ImageFont.truetype(FONT_PATH, 24)
        else:
            self.font = ImageFont.load_default()

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        current_time = time.time()

        # 지정된 간격마다 OCR 및 번역 수행
        if current_time - self.last_process_time > self.process_interval:
            self.last_process_time = current_time
            self.last_results = [] 
            
            try:
                ocr_data = pytesseract.image_to_data(img, lang='chi_sim+chi_tra', output_type=pytesseract.Output.DICT)
                
                n_boxes = len(ocr_data['text'])
                for i in range(n_boxes):
                    if int(ocr_data['conf'][i]) > 50 and ocr_data['text'][i].strip() != '':
                        text = ocr_data['text'][i]
                        x, y, w, h = (ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i])
                        
                        translated_text = self.translator.translate(text)
                        
                        self.last_results.append({
                            'box': (x, y, x + w, y + h),
                            'text': translated_text
                        })
            except Exception as e:
                pass

        # === 화면에 바운딩 박스와 텍스트 그리기 ===
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(img_pil)

        for result in self.last_results:
            x1, y1, x2, y2 = result['box']
            translated_text = result['text']

            draw.rectangle([x1, y1, x2, y2], outline="green", width=2)
            text_position = (x1, max(0, y1 - 30))
            draw.text(text_position, translated_text, font=self.font, fill=(0, 255, 0))

        img_result = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return av.VideoFrame.from_ndarray(img_result, format="bgr24")

st.markdown("### 1.5초 주기로 화면을 스캔하여 번역합니다.")

# WebRTC 컴포넌트 실행
webrtc_streamer(
    key="translator",
    video_processor_factory=VideoProcessor,
    rtc_configuration={
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    }
)
