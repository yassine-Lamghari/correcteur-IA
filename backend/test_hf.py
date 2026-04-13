from gradio_client import Client
import base64
with open(r'C:\Users\ASUS ROG\Desktop\yassine\examcorr\testimage.jpeg', 'rb') as f: b64 = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('utf-8')
client = Client('prithivMLmods/GLM-OCR-Demo')
print('Predicting...')
print(client.predict(task='Text', image_b64=b64, max_new_tokens_v=4096, gpu_timeout_v=60, api_name='/run_router'))
