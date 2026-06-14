#!/user/bin/env python3
# -*- coding: utf-8 -*-
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import glob
from common.logger import logger
from common.readFile import ReadFile



def emailSend(title='股市监控信息提醒'):
    logger.info("发送邮件开始...")
    yamlData = ReadFile.get_yamlAllPath("\\config\\emailConfig.yaml")
    emailCon = yamlData["emailService"]["oStMailCofig"]
    reportPath = yamlData["reportPath"]
    receiver = yamlData["receiver"]
    logger.info(receiver)

    # 配置SMTP服务器和发送者的信息
    smtp_server = emailCon["MAIL_SERVER"]
    port = emailCon["MAIL_PROT"]  # 或者使用465，取决于你的SMTP服务器配置
    sender_email = emailCon["MAIL_USERNAME"]
    password = emailCon["MAIL_PASSWORD"]

    # 创建邮件对象
    msg = MIMEMultipart()
    msg['From'] = "stockmonitor@qq.com"
    # msg['To'] = receiver
    msg['To'] = ', '.join(receiver)  # 将收件人列表用逗号分隔开，形成字符串
    msg['Subject'] = title

    # 邮件正文
    body = '您好，这是股市监控信息提醒，系统邮件请勿回复，谢谢！'
    msg.attach(MIMEText(body, 'plain'))

    # 定义模糊匹配的模式，例如匹配所有.txt文件
    pattern = '*.html'
    # 在当前目录或指定目录下查找匹配的文件
    # directory = getProjectPath() + "webToPython/webrunReport/reports"
    directory = ReadFile.getProjectPath() + reportPath

    # 使用 os.path.join 来合并目录和模式
    search_path = os.path.join(directory, pattern).replace("\\", '/')
    files = glob.glob(search_path)
    try:
        # 遍历文件并添加为附件
        for file in files:
            logger.info(f"file:{file}")
            with open(file, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(file)}")
                msg.attach(part)

        # 连接到SMTP服务器并发送邮件   避坑：需用SMTP_SSL  服务器环境会报错SMTPServerDisconnected("Connection unexpectedly closed")
        with smtplib.SMTP_SSL(smtp_server, port) as server:
            server.login(sender_email, password)
            text = msg.as_string()
            server.sendmail(sender_email, receiver, text)
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}")



def emailSendParameter(stock_list, title='今日推荐票信息'):
    logger.info("发送邮件开始...")
    yamlData = ReadFile.get_yamlAllPath("\\config\\emailConfig.yaml")
    emailCon = yamlData["emailService"]["oStMailCofig"]
    reportPath = yamlData["reportPath"]
    receiver = yamlData["receiver"]

    # 配置SMTP服务器和发送者的信息
    smtp_server = emailCon["MAIL_SERVER"]
    port = emailCon["MAIL_PROT"]  # 或者使用465，取决于你的SMTP服务器配置
    sender_email = emailCon["MAIL_USERNAME"]
    password = emailCon["MAIL_PASSWORD"]

    # 创建邮件对象
    msg = MIMEMultipart()
    msg['From'] = "stockmonitor@qq.com"
    # msg['To'] = receiver
    msg['To'] = ', '.join(receiver)  # 将收件人列表用逗号分隔开，形成字符串
    msg['Subject'] = title

    # 邮件正文
    body = f'您好，这是今日推荐票信息：{stock_list}，\n \n \n 系统邮件请勿回复，谢谢！'
    msg.attach(MIMEText(body, 'plain'))

    # 定义模糊匹配的模式，例如匹配所有.txt文件
    pattern = '*.html'
    # 在当前目录或指定目录下查找匹配的文件
    # directory = getProjectPath() + "webToPython/webrunReport/reports"
    directory = ReadFile.getProjectPath() + reportPath

    # 使用 os.path.join 来合并目录和模式
    search_path = os.path.join(directory, pattern).replace("\\", '/')
    files = glob.glob(search_path)
    try:
        # 遍历文件并添加为附件
        for file in files:
            logger.info(f"file:{file}")
            with open(file, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(file)}")
                msg.attach(part)

        # 连接到SMTP服务器并发送邮件   避坑：需用SMTP_SSL  服务器环境会报错SMTPServerDisconnected("Connection unexpectedly closed")
        with smtplib.SMTP_SSL(smtp_server, port) as server:
            server.login(sender_email, password)
            text = msg.as_string()
            server.sendmail(sender_email, receiver, text)
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

def emailSendContent(content, title='公告变化提醒'):
    logger.info("发送邮件开始...")
    yamlData = ReadFile.get_yamlAllPath("\\config\\emailConfig.yaml")
    emailCon = yamlData["emailService"]["oStMailCofig"]
    receiver = yamlData["receiver"]

    smtp_server = emailCon["MAIL_SERVER"]
    port = emailCon["MAIL_PROT"]
    sender_email = emailCon["MAIL_USERNAME"]
    password = emailCon["MAIL_PASSWORD"]

    msg = MIMEMultipart()
    msg['From'] = "stockmonitor@qq.com"
    msg['To'] = ', '.join(receiver)
    msg['Subject'] = title

    msg.attach(MIMEText(content, 'plain'))

    try:
        with smtplib.SMTP_SSL(smtp_server, port) as server:
            server.login(sender_email, password)
            text = msg.as_string()
            server.sendmail(sender_email, receiver, text)
        print("邮件发送成功！")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


if __name__ == '__main__':
    print("发送邮件开始")
    emailSend('600689 股票监控信息提醒')
    emailSendParameter(['600689', '600690', '600691'])