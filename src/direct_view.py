import cv2
import os
import datetime

PHOTO_DIR = os.path.expanduser(r"~\Pictures\Camera Roll")
os.makedirs(PHOTO_DIR, exist_ok=True)

def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    window_name = "Live Camera - Press [SPACE] to Save Photo | [Q] to Exit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 640)
    
    # Set window on top initially so user sees it right away
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        # Mirror display
        frame = cv2.flip(frame, 1)

        # Show on window
        cv2.imshow(window_name, frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27: # 'q' or ESC
            break
        elif key == 32: # SPACE key to capture photo
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(PHOTO_DIR, f"Photo_{ts}.jpg")
            cv2.imwrite(filename, frame)
            print(f"Captured photo: {filename}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
