import cv2
from flask import Flask, Response

app = Flask(__name__)

# Tente mudar esse número para 1 ou 2 se o 0 não funcionar
camera_index = 0 
camera = cv2.VideoCapture(camera_index)

if not camera.isOpened():
    print(f"ERRO: Não foi possível abrir a câmera no índice {camera_index}")
else:
    print(f"SUCESSO: Câmera {camera_index} aberta corretamente!")

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            print("Falha ao ler frame da câmera")
            break
        else:
            # Reduz um pouco a resolução para não pesar na rede corporativa
            frame = cv2.resize(frame, (640, 480))
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("Servidor de Câmera rodando em http://localhost:5000/video")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)