import json

import cv2
import numpy as np


class ZoneMarker:
    def __init__(self, video_path):
        self.cap = cv2.VideoCapture(video_path)
        self.points = []
        self.zones = []
        self.current_zone = []
        self.drawing = False

        # Берем первый кадр для разметки
        ret, self.frame = self.cap.read()
        if not ret:
            raise Exception("Не удалось прочитать видео")

        self.height, self.width = self.frame.shape[:2]

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.points.append((x, y))
            self.current_zone.append((x, y))
            self.drawing = True

        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            # Показываем предварительный вид
            temp_frame = self.frame.copy()
            if len(self.current_zone) > 1:
                pts = np.array(self.current_zone, np.int32)
                cv2.polylines(temp_frame, [pts], False, (0, 255, 0), 2)
            if self.current_zone:
                cv2.line(temp_frame, self.current_zone[-1], (x, y), (0, 255, 0), 2)
            cv2.imshow("Zone Marker", temp_frame)

        elif event == cv2.EVENT_RBUTTONDOWN:
            if len(self.current_zone) >= 3:
                self.zones.append(self.current_zone.copy())
                print(f"Зона {len(self.zones)} добавлена: {self.current_zone}")
                self.current_zone = []
                self.drawing = False
                self.redraw()

    def redraw(self):
        temp_frame = self.frame.copy()

        # Рисуем все завершенные зоны
        for i, zone in enumerate(self.zones):
            pts = np.array(zone, np.int32)
            cv2.polylines(temp_frame, [pts], True, (0, 0, 255), 2)
            # Центр для текста
            center_x = sum(p[0] for p in zone) // len(zone)
            center_y = sum(p[1] for p in zone) // len(zone)
            cv2.putText(
                temp_frame,
                f"Zone {i + 1}",
                (center_x - 30, center_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

        # Рисуем текущую зону
        if len(self.current_zone) > 1:
            pts = np.array(self.current_zone, np.int32)
            cv2.polylines(temp_frame, [pts], False, (0, 255, 0), 2)

        cv2.imshow("Zone Marker", temp_frame)

    def run(self):
        cv2.namedWindow("Zone Marker")
        cv2.setMouseCallback("Zone Marker", self.mouse_callback)

        print("Инструкция:")
        print("- ЛКМ: Добавить точку зоны")
        print("- ПКМ: Завершить текущую зону (минимум 3 точки)")
        print("- 's': Сохранить зоны в файл")
        print("- 'c': Очистить текущую зону")
        print("- 'q': Выйти")

        self.redraw()

        while True:
            key = cv2.waitKey(1) & 0xFF

            if key == ord("s"):
                self.save_zones()
            elif key == ord("c"):
                self.current_zone = []
                self.redraw()
            elif key == ord("q"):
                break

        cv2.destroyAllWindows()
        self.cap.release()

    def save_zones(self):
        zones_data = {
            "zones": self.zones,
            "image_size": {"width": self.width, "height": self.height},
        }

        with open("danger_zones.json", "w") as f:
            json.dump(zones_data, f, indent=2)

        print(f"Сохранено {len(self.zones)} зон в danger_zones.json")

        # Также выводим код для вставки в detector.py
        print("\nКод для detector.py:")
        for i, zone in enumerate(self.zones):
            print("DangerZone(")
            print(f"    points={zone},")
            print(f"    name='Danger Zone {i + 1}',")
            print("    safe_distance=100.0")
            print("),")


def main():
    video_path = "data/repairs.mov"  # Укажите путь к вашему видео
    marker = ZoneMarker(video_path)
    marker.run()


if __name__ == "__main__":
    main()
