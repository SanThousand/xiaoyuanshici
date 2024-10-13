import os
import cv2
import requests
import json
from paddleocr import PaddleOCR
import time
import numpy as np

# 全局初始化OCR对象加快速度
ocr = PaddleOCR(use_angle_cls=False, lang='ch', show_log=False)
# 配置大模型的url和key
URL = ""
KEY = ""
#大模型的名称
MODLE = ""

def get_pictures(picture_name = 'screenshot.png'):
    """
    通过ADB获取当前手机截图并保存到本地
    """
    #获取时间戳命名该文件
    os.system(f"adb shell screencap -p /sdcard/Download/{picture_name}")
    os.system(f"adb pull /sdcard/Download/{picture_name} {picture_name}")
    
    return cv2.imread(picture_name)

def compare_images(img1, img2):
    """
    比较两张图像在指定区域是否有明显变化
    :param img1: 前一张截图 (numpy数组)
    :param img2: 当前截图 (numpy数组)
    :param threshold: 差异阈值，默认为10
    :return: 是否有变化（布尔值）
    """
    if img1 is None or img2 is None:
        return True  # 如果是首次运行或图像为空，直接认为有变化

    # 裁剪指定区域 (x 轴从 320 到 399，y 轴从 65 到 109)
    img1_cropped = img1[65:109, 320:399]  # 裁剪 y 轴从 65 到 109，x 轴从 320 到 399
    img2_cropped = img2[65:109, 320:399]  # 裁剪 y 轴从 65 到 109，x 轴从 320 到 399

    # 计算两张图片的差异
    diff = cv2.absdiff(img1_cropped, img2_cropped)
    
    # 将差异图片转换为灰度图
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    
    # 计算差异的平均值
    mean_diff = np.mean(gray_diff)
    
    # 打印差异的平均值，便于调试
    print(f"图像差异值: {mean_diff}")

    # 保存裁剪后的图像用于调试
    cv2.imwrite("img1_cropped.png", img1_cropped)
    cv2.imwrite("img2_cropped.png", img2_cropped)

    # 如果差异大于设定的阈值，认为图片有变化
    return 0 < mean_diff < 10


def get_text_positions(cropped_image):
    """
    提取文本内容以及坐标位置
    """
    start_time = time.time()
    text_ocr = ocr.ocr(cropped_image, cls=True)
    
    question = ""
    options = []

    for i in range(len(text_ocr)):
        for item in text_ocr[i]:
            coordinates = item[0]
            y_min = min(coordinates[0][1], coordinates[1][1], coordinates[2][1], coordinates[3][1])
            y_max = max(coordinates[0][1], coordinates[1][1], coordinates[2][1], coordinates[3][1])
            text_info = item[1][0]
            if y_min > 495 and y_max < 710:
                question += text_info
            if y_min > 710:
                x, y = coordinates[0]
                # x_center = (coordinates[0][0] + coordinates[1][0] + coordinates[2][0] + coordinates[3][0]) / 4
                # y_center = (coordinates[0][1] + coordinates[1][1] + coordinates[2][1] + coordinates[3][1]) / 4
                options.append((text_info, (x, y)))   
                     
    # 如果问题为空，或者依然包含无效字符，跳过
    if not question.strip():
        return None, None
    
    end_time = time.time()
    print(f"get_text_positions 运行时间: {end_time - start_time} 秒")
    return question, options

def get_answer(question, options):
    """
    利用大模型获取答案坐标
    """
    start_time = time.time()
    for _ in range(10):
        headers = {
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": MODLE,
            "temperature": 0.7, 
            "messages": [
                {
                    "role": 'user',
                    "content": f'''
                    你是一个中小学古诗词高手，从指定问题中挑选正确的选项，选项以列表的形式存在，列表中包含选项和坐标，你只需要回复列表的索引值即可，除了索引值不要回复任何多余的内容，问题：{question}。选项：{options}
                    '''
                },
            ]
        }
    
        print(f'问题：{question}。选项：{options}')
        data = json.dumps(data)
        response = requests.post(URL, headers=headers, data=data)
        # print(response.json())
        story = response.json()["choices"][0]["message"]["content"]
        print(story)
        
        try:
            answer = options[int(story)][1]
            print(f"答案坐标：{answer}")
            end_time = time.time()
            print(f"get_answer 运行时间: {end_time - start_time} 秒")
            return answer
        except Exception:
            print("模型回复错误，正在重试")
            time.sleep(2)
            continue
        
    print("达到最大重试次数，未能获取有效答案")
    end_time = time.time()
    print(f"get_answer 运行时间: {end_time - start_time} 秒")
    return

def adb_click(answer):
    """
    模拟ADB点击题目所在位置
    """
    start_time = time.time()
    print(f"点击位置：x: {answer[0]}, y: {answer[1]}")
    os.system(f"adb shell input tap {answer[0]} {answer[1]}")
    end_time = time.time()
    print(f"adb_click 运行时间: {end_time - start_time} 秒")
    
def auto_click():
    """
    自动下一次比赛
    """
    os.system("adb shell input tap 357 1027")
    time.sleep(2)
    os.system("adb shell input tap 519 1226")
    time.sleep(2)
    #查看PK详情按钮
    # os.system("adb shell input tap 351 1080")
    # time.sleep(2)
    #再来一局
    os.system("adb shell input tap 384 1214")
    time.sleep(2)
    #开始PK（填写开始pk的坐标）
    os.system("adb shell input tap 374 1123")
    time.sleep(5)
    #再来一局
    os.system("adb shell input tap 384 1214")
    time.sleep(1)
    #开始PK（填写开始pk的坐标）
    os.system("adb shell input tap 374 1123")
    time.sleep(1)

def main():
    start_time = time.time()
    #当前题目截图
    last_image = cv2.imread("test.png")
    while True:
        for i in range(8):
            while True:
                # 获取截图并获取图片地址
                image = get_pictures("image.png")
                
                # 图片比对,有变化则比对继续向下执行
                if not compare_images(last_image, image):
                    print("无变化等待下次检测。")
                    time.sleep(0.3)
                    continue
                #防止题目未加载完成，等待1秒
                time.sleep(0.3)
                #重写拉取题目
                image = get_pictures("image.png")

                # 如果有变化继续处理
                question, options = get_text_positions(image)
                
                if question is None or options is None:
                    time.sleep(0.5)
                    continue
                
                
                answer = get_answer(question, options)
                if answer:
                    adb_click(answer)
                    last_image = image  # 更新 last_image
                break  # 退出 while 循环，进入下一题
        
        end_time = time.time()
        print(f"第 {i+1} 道题完成，总运行时间: {end_time - start_time} 秒")
        #等待答题结束
        time.sleep(16)
        auto_click()

if __name__ == "__main__":
    main()