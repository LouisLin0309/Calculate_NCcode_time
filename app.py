from flask import Flask, request, jsonify
import re
import math

app = Flask(__name__)

# HTML 表單模板
HTML_FORM = '''
<!doctype html>
<html>
<head><title>NC Code Processing Time Calculator</title></head>
<body>
    <h2>NC Code Processing Time Calculator</h2>
    <form method="post">
        NC Code:<br>
        <textarea name="nc_code" rows="5" cols="50"></textarea><br>
        Start X:<br>
        <input type="text" name="start_x" value="0"><br>
        Start Y:<br>
        <input type="text" name="start_y" value="0"><br>
        Start Z:<br>
        <input type="text" name="start_z" value="200"><br>
        Acceleration (a):<br>
        <input type="text" name="a" value="187.5"><br><br>
        <input type="submit" value="Calculate Time">
    </form>
</body>
</html>
'''
# 全局變數
nc_code = ""
start_x1 = 0
start_y1 = 0
start_z1 = 200
cutting_width = 0
def calculate_distance(start_x, start_y, start_z, end_x, end_y, end_z):
    return math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2 + (end_z - start_z) ** 2)

def calculate_arc_distance_G2(center_x, center_y, start_x, start_y, end_x, end_y):
    radius = calculate_distance(center_x, center_y, 0, start_x, start_y, 0)
    start_angle = math.atan2(start_y - center_y, start_x - center_x)
    end_angle = math.atan2(end_y - center_y, end_x - center_x)
    if start_angle < 0:
        start_angle = 2*math.pi+start_angle
    if end_angle < 0:
        end_angle = 2*math.pi+end_angle

    # 考慮圓弧的方向，逆時針(G3)為正，順時針(G2)為負
    if start_angle > end_angle:
        angle = start_angle - end_angle
    else:
        angle = 2 * math.pi - (end_angle - start_angle)

    return radius * angle
def calculate_arc_distance_G3(center_x, center_y, start_x, start_y, end_x, end_y):
    radius = calculate_distance(center_x, center_y, 0, start_x, start_y, 0)
    start_angle = math.atan2(start_y - center_y, start_x - center_x)
    end_angle = math.atan2(end_y - center_y, end_x - center_x)
    if start_angle < 0:
        start_angle=2*math.pi+start_angle
    if end_angle < 0:
        end_angle=2*math.pi+end_angle

    # 考慮圓弧的方向，逆時針(G3)為正，順時針(G2)為負
    if start_angle < end_angle:
        angle = end_angle - start_angle
    else:
        angle = 2 * math.pi - (start_angle - end_angle)

    return radius * angle

def time_to_reach_speed(F, a):   #F=(mm/min),a=mm/s^2
    # 計算達到速度 F 所需的時間(sec)
    return (F/60) / a

def distance_to_reach_speed(F, a):
    # 計算達到速度 F 所需的距離(mm)
    return 0.5 * a * ((F/60)/a)**2

def calculate_processing_time_with_acceleration(nc_code, a=187.5): # a 為加速度, 默認值為 10000 mm/s^2
    lines = nc_code.split('\n')
    start_x, start_y, start_z = start_x1, start_y1, start_z1
    end_x, end_y, end_z = start_x1, start_y1, start_z1
    center_x, center_y = 0, 0
    processing_times = []
    feed_rate = 10000

    for line in lines:
        line = line.strip()

        matches = re.finditer(r'([XYZF])((-?\d*\.?\d+)|\(.*?\))|([IJ])=AC\((-?\d*\.?\d*)\)', line)
        if matches:
            for match in matches:
                if match.group(1):  # 如果匹配了X、Y、Z、F
                    axis = match.group(1)
                    value = match.group(2) if match.group(2) else match.group(3)
                else:  # 如果匹配了I、J
                    axis = match.group(4)
                    value = match.group(5)


                if axis == 'X':
                    end_x = float(value)
                elif axis == 'Y':
                    end_y = float(value)
                elif axis == 'Z':
                    end_z = float(value)
                elif axis == 'F':
                    feed_rate = float(value)
                elif axis == 'I':
                    center_x = float(value)
                elif axis == 'J':
                    center_y = float(value)
            if 'G2' in line or 'G02' in line:
                distance = calculate_arc_distance_G2(center_x, center_y, start_x, start_y, end_x, end_y)
                d_accel = distance_to_reach_speed(feed_rate, a) 
                if distance <= 2 * d_accel: #此情況因應該很難發生
                    # 如果路徑太短，無法達到最大進給速度
                    v_max = math.sqrt(2 * a * distance / 2) 
                    t_accel = time_to_reach_speed(v_max, a)
                    processing_time = 2 * t_accel
                    processing_times.append(processing_time)
                else:
                    # 計算加速、匀速和減速的時間
                    t_accel = time_to_reach_speed(feed_rate, a)
                    t_constant = (distance - 2 * d_accel) *60/ feed_rate
                    processing_time = 2 * t_accel + t_constant                   
                    processing_times.append(processing_time)
            elif 'G3' in line or 'G03' in line:
                distance = calculate_arc_distance_G3(center_x, center_y, start_x, start_y, end_x, end_y)
                d_accel = distance_to_reach_speed(feed_rate, a) 
                if distance <= 2 * d_accel: #此情況因應該很難發生
                    # 如果路徑太短，無法達到最大進給速度
                    v_max = math.sqrt(2 * a * distance / 2) 
                    t_accel = time_to_reach_speed(v_max, a)
                    processing_time = 2 * t_accel
                    processing_times.append(processing_time)
                else:
                    # 計算加速、匀速和減速的時間
                    t_accel = time_to_reach_speed(feed_rate, a)
                    t_constant = (distance - 2 * d_accel) *60/ feed_rate
                    processing_time = 2 * t_accel + t_constant                   
                    processing_times.append(processing_time)

            elif 'X' in line or 'Y' in line or 'Z' in line:
                if 'G0' in line and 'G01' not in line:
                     feed_rate = 10000
                distance = calculate_distance(start_x, start_y, start_z, end_x, end_y, end_z)
                d_accel = distance_to_reach_speed(feed_rate, a) 
                if distance <= 2 * d_accel: #此情況因應該很難發生
                    # 如果路徑太短，無法達到最大進給速度
                    v_max = math.sqrt(2 * a * distance / 2) 
                    t_accel = time_to_reach_speed(v_max, a)
                    processing_time = 2 * t_accel
                    processing_times.append(processing_time)
                else:
                    # 計算加速、匀速和減速的時間
                    t_accel = time_to_reach_speed(feed_rate, a)
                    t_constant = (distance - 2 * d_accel) *60/ feed_rate
                    processing_time = 2 * t_accel + t_constant                   
                    processing_times.append(processing_time)
                
            else:
                processing_times.append(0)    
            
            
            start_x, start_y, start_z = end_x, end_y, end_z

    return processing_times



# Function to calculate time

@app.route('/calculate_time', methods=['GET', 'POST'])
def calculate_time_api():
    if request.method == 'POST':
        # 從表單獲取數據
        nc_code = request.form['nc_code']
        start_x = float(request.form.get('start_x', 0))
        start_y = float(request.form.get('start_y', 0))
        start_z = float(request.form.get('start_z', 200))
        a = float(request.form.get('a', 187.5))

        # 執行計算
        processing_times = calculate_processing_time_with_acceleration(nc_code, a)
        total_time = sum(processing_times)

        # 返回計算結果
        return f"Total processing time: {total_time:.2f} seconds"
    else:
        # 返回 HTML 表單
        return HTML_FORM
@app.route('/')
def home():
    return "Welcome to the NC Code Processing Time Calculator API!"
if __name__ == '__main__':
    app.run(debug=True)