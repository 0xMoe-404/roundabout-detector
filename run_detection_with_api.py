"""
Integration script to send car detection data to Flask API
This script runs the roundabout detection and sends results to the API in real-time
"""
import sys
import requests
from datetime import datetime
import time

# Add the path to import from roundabout_detection
sys.path.append('Car Detect2')

# Import necessary functions and constants from the detection script
from roundabout_detection import *

# API configuration
API_URL = 'http://localhost:5000/api/roundabout/test-001/update'
ROUNDABOUT_ID = 'test-001'


def send_to_api(cars_data, stats_data):
    """Send detection data to the Flask API"""
    try:
        payload = {
            'cars': cars_data,
            'stats': stats_data
        }
        # Increased timeout to 5 seconds to prevent timeouts
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            return True
        else:
            print(f"API Error: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        # print(f"Failed to send to API: {e}") # Suppress frequent errors
        return False


def main_with_api():
    """Modified main function that sends data to API"""
    args = parse_args()
    
    # Load YOLO model
    model = YOLO(args.model)
    
    cap = open_video_capture(args.source)
    
    # Build polygons
    roundabout_polygon = None
    first_car_zone_polygon = None
    second_car_zone_polygon = None
    
    # For tracking
    frame_count = 0
    total_vehicles_entered = 0
    total_vehicles_exited = 0
    total_penalties = 0
    
    # Track state of each car: {track_id: was_in_roundabout (bool)}
    track_states = {}
    
    # Track last seen frame for cleanup
    active_tracks = {}
    EXIT_THRESHOLD_FRAMES = 30  # Cleanup threshold
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            if roundabout_polygon is None:
                roundabout_polygon = build_roundabout_polygon(frame.shape)
                first_car_zone_polygon = build_first_car_zone_polygon(frame.shape)
                second_car_zone_polygon = build_second_car_zone_polygon(frame.shape)
            
            # Run YOLO tracking (persist=True for tracking)
            results = model.track(source=frame, conf=args.conf, iou=args.iou, persist=True, verbose=False)
            
            # Track vehicles and zones
            vehicle_counts = {name: 0 for name in VEHICLE_CLASSES}
            roundabout_counts = {name: 0 for name in VEHICLE_CLASSES}
            first_car_zone_counts = {name: 0 for name in VEHICLE_CLASSES}
            second_car_zone_counts = {name: 0 for name in VEHICLE_CLASSES}
            penalty_count = 0
            
            # Cars data to send to API
            cars_in_roundabout = []
            
            current_frame_track_ids = set()
            
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                
                for box in boxes:
                    cls_id = int(box.cls[0].item()) if box.cls is not None else None
                    conf = float(box.conf[0].item()) if box.conf is not None else 0.0
                    
                    # Get track ID if available
                    track_id = int(box.id[0].item()) if box.id is not None else None
                    
                    if cls_id is None or cls_id < 0 or cls_id >= len(COCO_CLASSES):
                        continue
                    
                    cls_name = COCO_CLASSES[cls_id]
                    if cls_name not in VEHICLE_CLASSES:
                        continue
                    
                    # Box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                    
                    # Update counts
                    vehicle_counts[cls_name] += 1
                    
                    # Center point
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    
                    in_roundabout = is_point_in_roundabout((cx, cy), roundabout_polygon)
                    in_first_car_zone = is_point_in_first_car_zone((cx, cy), first_car_zone_polygon)
                    in_second_car_zone = is_point_in_second_car_zone((cx, cy), second_car_zone_polygon)
                    
                    # ENTRY / EXIT LOGIC based on Roundabout Zone
                    if track_id is not None:
                        current_frame_track_ids.add(track_id)
                        active_tracks[track_id] = frame_count
                        
                        was_in_roundabout = track_states.get(track_id, False)
                        
                        if in_roundabout and not was_in_roundabout:
                            # Transition: Outside -> Inside = ENTRY
                            total_vehicles_entered += 1
                            track_states[track_id] = True
                        elif not in_roundabout and was_in_roundabout:
                            # Transition: Inside -> Outside = EXIT
                            total_vehicles_exited += 1
                            track_states[track_id] = False
                        elif in_roundabout:
                            # Keep state as True if already inside
                            track_states[track_id] = True
                    
                    if in_roundabout:
                        roundabout_counts[cls_name] += 1
                    
                    if in_first_car_zone:
                        first_car_zone_counts[cls_name] += 1
                    
                    if in_second_car_zone:
                        second_car_zone_counts[cls_name] += 1
                    
                    # Penalty detection
                    is_penalty = False
                    if in_second_car_zone and sum(first_car_zone_counts.values()) > 0:
                        is_penalty = True
                        penalty_count += 1
                    
                    # If car is in roundabout, add to API data
                    if in_roundabout:
                        car_data = {
                            'id': f'car-{track_id}' if track_id is not None else f'car-{frame_count}-{cx}-{cy}',
                            'type': cls_name,
                            'confidence': round(conf, 2),
                            'position': {'x': cx, 'y': cy},
                            'inFirstZone': in_first_car_zone,
                            'inSecondZone': in_second_car_zone,
                            'isPenalty': is_penalty,
                            'timestamp': datetime.now().isoformat()
                        }
                        cars_in_roundabout.append(car_data)
                    
                    # Draw on frame
                    if is_penalty:
                        color = (0, 0, 255)  # Red
                        label = f"PENALTY {cls_name} {track_id}"
                    elif in_first_car_zone:
                        color = (0, 255, 0)  # Green
                        label = f"{cls_name} {track_id}"
                    elif in_second_car_zone:
                        color = (0, 255, 255)  # Yellow
                        label = f"{cls_name} {track_id}"
                    elif in_roundabout:
                        color = (255, 255, 0)  # Cyan
                        label = f"{cls_name} {track_id}"
                    else:
                        color = (255, 0, 0)  # Blue
                        label = f"{cls_name} {track_id}"
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                    cv2.rectangle(frame, (x1, y1 - th - 4), (x1 + tw, y1), color, -1)
                    cv2.putText(frame, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
            
            # Cleanup old tracks
            ids_to_remove = []
            for track_id, last_seen in active_tracks.items():
                if frame_count - last_seen > EXIT_THRESHOLD_FRAMES:
                    ids_to_remove.append(track_id)
            
            for track_id in ids_to_remove:
                del active_tracks[track_id]
                if track_id in track_states:
                    del track_states[track_id]
            
            # Send to API every frame
            total_in_roundabout = sum(roundabout_counts.values())
            total_penalties += penalty_count
            
            stats_data = {
                'vehicleEntry': total_vehicles_entered,
                'vehicleExit': total_vehicles_exited,
                'laneUtilization': total_in_roundabout, # Sending raw count as requested
                'congestionLevel': 'Critical' if total_in_roundabout > 8 else 'High' if total_in_roundabout > 5 else 'Moderate' if total_in_roundabout > 2 else 'Low',
                'penaltyCount': total_penalties,
                'wrongWay': 0,
                'illegalUTurn': 0,
                'speeding': 0
            }
            
            # Send to API
            send_to_api(cars_in_roundabout, stats_data)
            
            # Draw HUD
            draw_hud(frame, vehicle_counts, roundabout_counts, penalty_count)
            
            # Show frame
            if args.show:
                cv2.imshow("Vehicle Detection - API Integration", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    print("Starting roundabout detection with API integration...")
    print(f"Sending data to: {API_URL}")
    print("Make sure the Flask API is running on http://localhost:5000")
    print()
    main_with_api()
