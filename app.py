from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Mock data structure matching frontend expectations
DISTRICTS = [
    {
        'id': 'north',
        'name': 'شمال الرياض',
        'nameAr': 'المنطقة الشمالية',
        'totalRoundabouts': 12,
        'activeAlerts': 3,
        'congestionScore': 72,
        'severity': 'concern',
        'latitude': 24.8,
        'longitude': 46.7,
    },
    {
        'id': 'south',
        'name': 'جنوب الرياض',
        'nameAr': 'المنطقة الجنوبية',
        'totalRoundabouts': 8,
        'activeAlerts': 1,
        'congestionScore': 45,
        'severity': 'attention',
        'latitude': 24.6,
        'longitude': 46.7,
    },
    {
        'id': 'east',
        'name': 'شرق الرياض',
        'nameAr': 'المنطقة الشرقية',
        'totalRoundabouts': 11,
        'activeAlerts': 5,
        'congestionScore': 88,
        'severity': 'critical',
        'latitude': 24.7,
        'longitude': 46.8,
    },
    {
        'id': 'west',
        'name': 'غرب الرياض',
        'nameAr': 'المنطقة الغربية',
        'totalRoundabouts': 9,
        'activeAlerts': 0,
        'congestionScore': 28,
        'severity': 'optimal',
        'latitude': 24.7,
        'longitude': 46.6,
    },
    {
        'id': 'central',
        'name': 'وسط الرياض',
        'nameAr': 'المنطقة الوسطى',
        'totalRoundabouts': 5,
        'activeAlerts': 2,
        'congestionScore': 65,
        'severity': 'concern',
        'latitude': 24.7,
        'longitude': 46.7,
    },
]

ROUNDABOUTS = [
    {
        'id': 'n-001',
        'name': 'King Fahd Rd & Olaya St',
        'districtId': 'north',
        'vehicleEntry': 1245,
        'vehicleExit': 1189,
        'entryTrend': 'up',
        'exitTrend': 'stable',
        'laneUtilization': 78,
        'congestionLevel': 'High',
        'riskyBehaviors': {'wrongWay': 3, 'illegalUTurn': 7, 'speeding': 12},
        'lastUpdated': datetime.now().isoformat(),
        'severityScore': 75,
        'latitude': 24.81,
        'longitude': 46.7,
    },
    {
        'id': 'test-001',
        'name': 'Test Roundabout (Live Detection)',
        'districtId': 'central',
        'vehicleEntry': 892,
        'vehicleExit': 905,
        'entryTrend': 'stable',
        'exitTrend': 'stable',
        'laneUtilization': 65,
        'congestionLevel': 'Moderate',
        'riskyBehaviors': {'wrongWay': 1, 'illegalUTurn': 3, 'speeding': 8},
        'lastUpdated': datetime.now().isoformat(),
        'severityScore': 52,
        'latitude': 24.71,
        'longitude': 46.69,
    },
]

ALERTS = [
    {
        'id': 'a-001',
        'roundaboutId': 'n-001',
        'roundaboutName': 'King Fahd Rd & Olaya St',
        'districtId': 'north',
        'districtName': 'Northern District',
        'severity': 'concern',
        'type': 'congestion',
        'message': 'High congestion - 78% lane utilization',
        'estimatedImpact': '8-minute average delay',
        'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
        'acknowledged': False,
        'severityScore': 75,
    },
]

# Store for cars currently in roundabouts
CARS_IN_ROUNDABOUTS = {
    'test-001': []
}


def generate_mock_car():
    """Generate a mock car for testing"""
    car_types = ['car', 'motorcycle', 'truck', 'bus']
    return {
        'id': f'car-{random.randint(1000, 9999)}',
        'type': random.choice(car_types),
        'confidence': round(random.uniform(0.7, 0.95), 2),
        'position': {
            'x': random.randint(100, 800),
            'y': random.randint(100, 600)
        },
        'inFirstZone': random.choice([True, False]),
        'inSecondZone': random.choice([True, False]),
        'isPenalty': False,
        'timestamp': datetime.now().isoformat()
    }


def update_realtime_data():
    """Simulate real-time data updates"""
    for roundabout in ROUNDABOUTS:
        # Skip the test roundabout as it receives real data
        if roundabout['id'] == 'test-001':
            continue
            
        # Update vehicle counts
        entry_delta = random.randint(-20, 20)
        exit_delta = random.randint(-20, 20)
        utilization_delta = random.randint(-3, 3)
        
        roundabout['vehicleEntry'] = max(200, roundabout['vehicleEntry'] + entry_delta)
        roundabout['vehicleExit'] = max(200, roundabout['vehicleExit'] + exit_delta)
        roundabout['laneUtilization'] = min(100, max(20, roundabout['laneUtilization'] + utilization_delta))
        
        # Update trends
        roundabout['entryTrend'] = 'up' if entry_delta > 5 else 'down' if entry_delta < -5 else 'stable'
        roundabout['exitTrend'] = 'up' if exit_delta > 5 else 'down' if exit_delta < -5 else 'stable'
        
        # Update congestion level
        util = roundabout['laneUtilization']
        if util >= 90:
            roundabout['congestionLevel'] = 'Critical'
        elif util >= 75:
            roundabout['congestionLevel'] = 'High'
        elif util >= 55:
            roundabout['congestionLevel'] = 'Moderate'
        else:
            roundabout['congestionLevel'] = 'Low'
        
        # Update severity score
        risky = roundabout['riskyBehaviors']
        severity = int(util * 0.6 + (risky['wrongWay'] * 2 + risky['illegalUTurn'] + risky['speeding']) * 0.4)
        roundabout['severityScore'] = min(100, severity)
        roundabout['lastUpdated'] = datetime.now().isoformat()
    
    # Mock car generation for test-001 removed to allow real data



# Background thread to update data
import threading

def background_updater():
    while True:
        time.sleep(5)  # Update every 5 seconds
        update_realtime_data()

# Start background updater
updater_thread = threading.Thread(target=background_updater, daemon=True)
updater_thread.start()


@app.route('/api/roundabouts', methods=['GET'])
def get_roundabouts():
    """Get all roundabouts"""
    return jsonify(ROUNDABOUTS)


@app.route('/api/districts', methods=['GET'])
def get_districts():
    """Get all districts"""
    return jsonify(DISTRICTS)


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts"""
    return jsonify(ALERTS)


@app.route('/api/roundabout/<roundabout_id>', methods=['GET'])
def get_roundabout(roundabout_id):
    """Get specific roundabout details"""
    roundabout = next((r for r in ROUNDABOUTS if r['id'] == roundabout_id), None)
    if roundabout:
        return jsonify(roundabout)
    return jsonify({'error': 'Roundabout not found'}), 404


@app.route('/api/roundabout/<roundabout_id>/cars', methods=['GET'])
def get_roundabout_cars(roundabout_id):
    """Get cars currently in the roundabout"""
    if roundabout_id not in CARS_IN_ROUNDABOUTS:
        CARS_IN_ROUNDABOUTS[roundabout_id] = []
    
    cars = CARS_IN_ROUNDABOUTS[roundabout_id]
    
    # Calculate summary statistics
    total_cars = len(cars)
    penalty_count = sum(1 for car in cars if car['isPenalty'])
    first_zone_count = sum(1 for car in cars if car['inFirstZone'])
    second_zone_count = sum(1 for car in cars if car['inSecondZone'])
    
    # Count by type
    car_types = {}
    for car in cars:
        car_type = car['type']
        car_types[car_type] = car_types.get(car_type, 0) + 1
    
    return jsonify({
        'roundaboutId': roundabout_id,
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'totalCars': total_cars,
            'penaltyCount': penalty_count,
            'firstZoneCount': first_zone_count,
            'secondZoneCount': second_zone_count,
            'carTypes': car_types
        },
        'cars': cars
    })


@app.route('/api/roundabout/<roundabout_id>/update', methods=['POST'])
def update_roundabout_cars(roundabout_id):
    """Update cars in the roundabout from detection system"""
    from flask import request
    
    data = request.json
    if not data or 'cars' not in data:
        return jsonify({'error': 'Invalid data format'}), 400
    
    # Update the cars data
    CARS_IN_ROUNDABOUTS[roundabout_id] = data['cars']
    
    # Also update roundabout statistics if provided
    if 'stats' in data:
        roundabout = next((r for r in ROUNDABOUTS if r['id'] == roundabout_id), None)
        if roundabout:
            stats = data['stats']
            if 'vehicleEntry' in stats:
                roundabout['vehicleEntry'] = stats['vehicleEntry']
            if 'vehicleExit' in stats:
                roundabout['vehicleExit'] = stats['vehicleExit']
            if 'laneUtilization' in stats:
                roundabout['laneUtilization'] = stats['laneUtilization']
            if 'congestionLevel' in stats:
                roundabout['congestionLevel'] = stats['congestionLevel']
            if 'penaltyCount' in stats:
                # Update risky behaviors
                roundabout['riskyBehaviors']['wrongWay'] = stats.get('wrongWay', 0)
                roundabout['riskyBehaviors']['illegalUTurn'] = stats.get('illegalUTurn', 0)
                roundabout['riskyBehaviors']['speeding'] = stats.get('speeding', 0)
            roundabout['lastUpdated'] = datetime.now().isoformat()
    
    return jsonify({
        'status': 'success',
        'roundaboutId': roundabout_id,
        'carsUpdated': len(data['cars'])
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("Starting Flask API server...")
    print("API will be available at http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  GET /api/roundabouts")
    print("  GET /api/districts")
    print("  GET /api/alerts")
    print("  GET /api/roundabout/<id>")
    print("  GET /api/roundabout/<id>/cars")
    print("  GET /api/health")
    app.run(debug=True, host='0.0.0.0', port=5000)
