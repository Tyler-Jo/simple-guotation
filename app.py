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
import threading  # 비동기 처리를 위해 추가

# 페이지 설정
st.set_page_config(page_title="실시간 중한 번역기", layout="wide")
st.title("📸 실시간 중국어 -> 한국어 번역기 (No Freeze)")

FONT_PATH = "NanumGothic.ttf"

class VideoProcessor:
    def __init__(self):
        self.translator = GoogleTranslator(source='zh-CN', target='ko')
        self.last_results = []       
        self.last_process_time = 0   
        self.process_interval = 1.5  
        self.is_processing = False  # 번역 작업이 백그라운드에서 진행 중인지 확인하는 플래그

        if os.path.exists(FONT_PATH):
            self.font = ImageFont.truetype(FONT_PATH, 24)
        else:
            self.font = ImageFont.load_default()

    # 무거운 작업(OCR + 인터넷 번역 통신)을 전담할 별도의 함수
    def perform_ocr_and_translate(self, img_copy):
        try:
            ocr_data = pytesseract.image_to_data(img_copy, lang='chi_sim+chi_tra', output_type=pytesseract.Output.DICT)
            
            temp_results = []
            n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                if int(ocr_data['conf'][i]) > 50 and ocr_data['text'][i].strip() != '':
                    text = ocr_data['text'][i]
                    x, y, w, h = (ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i])
                    
                    # 여기서 시간이 오래 걸리더라도 카메라 화면은 멈추지 않음!
                    translated_text = self.translator.translate(text)
                    
                    temp_results.append({
                        'box': (x, y, x + w, y + h),
                        'text': translated_text
                    })
            
            # 작업이 무사히 끝나면 화면에 그려질 결과를 업데이트
            self.last_results = temp_results
            
        except Exception as e:
            pass # 에러가 나도 조용히 넘어가서 앱 종료를 방지
            
        finally:
            # 작업이 끝났으므로 다음 1.5초 주기에 다시 실행될 수 있도록 플래그 해제
            self.is_processing = False

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        current_time = time.time()

        # 1.5초가 지났고 & 현재 백그라운드에서 번역이 돌아가고 있지 않을 때만 새로운 번역 지시
        if current_time - self.last_process_time > self.process_interval and not self.is_processing:
            self.last_process_time = current_time
            self.is_processing = True # 중복 실행 방지 잠금
            
            # OCR과 번역 작업을 메인 화면과 분리해서 백그라운드(스레드)로 던짐!
            threading.Thread(target=self.perform_ocr_and_translate, args=(img.copy(),)).start()

        # === 화면에 그리기 (번역 중이더라도 기존 결과물을 유지하며 카메라는 계속 흘러감) ===
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

st.markdown("### 비디오는 멈추지 않고, 번역만 1.5초마다 백그라운드에서 돌아갑니다.")

# 카메라 설정 롤백 완료
webrtc_streamer(
    key="translator",
    video_processor_factory=VideoProcessor,
    rtc_configuration={
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    }
)
