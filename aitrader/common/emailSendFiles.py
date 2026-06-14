#!/user/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import socket
import glob
from common.logger import logger
from common.readFile import ReadFile



def emailSend(title='股市监控信息提醒'):
    logger.info("发送邮件开始...")
    yamlData = ReadFile.get_yamlAllPath("/config/emailConfig.yaml")
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
        with smtplib.SMTP_SSL(smtp_server, port, timeout=30) as server:
            server.login(sender_email, password)
            text = msg.as_string()
            server.sendmail(sender_email, receiver, text)
        logger.info("邮件发送成功！")
    except Exception as e:
        logger.info(f"邮件发送失败: {e}", file=sys.stderr)
        traceback.logger.info_exc(file=sys.stderr)



def emailSendParameter(stock_list, title='今日推荐票信息'):
    logger.info("发送邮件开始...")
    yamlData = ReadFile.get_yamlAllPath("/config/emailConfig.yaml")
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
        with smtplib.SMTP_SSL(smtp_server, port, timeout=30) as server:
            server.login(sender_email, password)
            text = msg.as_string()
            server.sendmail(sender_email, receiver, text)
        logger.info("邮件发送成功！")
    except Exception as e:
        logger.info(f"邮件发送失败: {e}", file=sys.stderr)
        traceback.logger.info_exc(file=sys.stderr)

def emailSendContent(content, title='公告变化提醒'):
    logger.info(f"[EMAIL] ====== 开始发送邮件 ======")
    logger.info(f"[EMAIL] 标题: {title}")
    logger.info(f"[EMAIL] 正文长度: {len(content)} 字符")

    # Step 1: 加载配置
    logger.info(f"[EMAIL] Step1: 加载邮件配置...")
    try:
        yamlData = ReadFile.get_yamlAllPath("/config/emailConfig.yaml")
        logger.info(f"[EMAIL] Step1: 配置加载成功, keys={list(yamlData.keys())}")
    except Exception as e:
        logger.info(f"[EMAIL] Step1 失败: 无法读取 emailConfig.yaml: {e}")
        traceback.logger.info_exc()
        return False

    emailCon = yamlData["emailService"]["oStMailCofig"]
    receiver = yamlData["receiver"]
    smtp_server = emailCon["MAIL_SERVER"]
    port = emailCon["MAIL_PROT"]
    sender_email = emailCon["MAIL_USERNAME"]
    password = emailCon["MAIL_PASSWORD"]

    logger.info(f"[EMAIL] Step2: SMTP配置 smtp_server={smtp_server} port={port}")
    logger.info(f"[EMAIL] Step2: sender={sender_email} receiver={receiver}")
    logger.info(f"[EMAIL] Step2: password={'***' if password else 'EMPTY!'} (长度={len(password) if password else 0})")

    # 校验配置
    if not smtp_server:
        logger.info(f"[EMAIL] Step2 失败: MAIL_SERVER 为空", file=sys.stderr)
        return False
    if not password:
        logger.info(f"[EMAIL] Step2 失败: MAIL_PASSWORD 为空", file=sys.stderr)
        return False
    if not receiver:
        logger.info(f"[EMAIL] Step2 失败: receiver 为空", file=sys.stderr)
        return False

    # Step 3: 构建邮件
    logger.info(f"[EMAIL] Step3: 构建邮件对象...")
    msg = MIMEMultipart()
    msg['From'] = "stockmonitor@qq.com"
    msg['To'] = ', '.join(receiver) if isinstance(receiver, list) else receiver
    msg['Subject'] = title
    msg.attach(MIMEText(content, 'plain'))
    logger.info(f"[EMAIL] Step3: 邮件对象构建完成")

    # Step 4: 连接 SMTP
    logger.info(f"[EMAIL] Step4: 连接 SMTP {smtp_server}:{port} (timeout=30s)...")
    try:
        server = smtplib.SMTP_SSL(smtp_server, port, timeout=30)
        logger.info(f"[EMAIL] Step4: SMTP 连接成功, 开始登录...")
    except socket.gaierror as e:
        logger.info(f"[EMAIL] Step4 失败: DNS 解析失败 {smtp_server}: {e}", file=sys.stderr)
        return False
    except socket.timeout as e:
        logger.info(f"[EMAIL] Step4 失败: 连接超时 {smtp_server}:{port}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        logger.info(f"[EMAIL] Step4 失败: 连接异常 {type(e).__name__}: {e}", file=sys.stderr)
        traceback.logger.info_exc(file=sys.stderr)
        return False

    # Step 5: 登录
    try:
        server.login(sender_email, password)
        logger.info(f"[EMAIL] Step5: 登录成功")
    except smtplib.SMTPAuthenticationError as e:
        logger.info(f"[EMAIL] Step5 失败: 认证失败, 请检查邮箱授权码: {e}", file=sys.stderr)
        try:
            server.quit()
        except Exception:
            pass
        return False
    except Exception as e:
        logger.info(f"[EMAIL] Step5 失败: 登录异常 {type(e).__name__}: {e}", file=sys.stderr)
        traceback.logger.info_exc(file=sys.stderr)
        try:
            server.quit()
        except Exception:
            pass
        return False

    # Step 6: 发送
    logger.info(f"[EMAIL] Step6: 发送邮件...")
    try:
        text = msg.as_string()
        logger.info(f"[EMAIL] Step6: 邮件序列化完成, 大小={len(text)} 字节")
        send_result = server.sendmail(sender_email, receiver, text)
        logger.info(f"[EMAIL] Step6: sendmail 返回: {send_result} (空dict=全部成功)")
        server.quit()
        logger.info(f"[EMAIL] Step6: 发送完成, SMTP 连接已关闭")
        logger.info(f"[EMAIL] ====== 邮件发送成功 ======")
        return True
    except Exception as e:
        logger.info(f"[EMAIL] Step6 失败: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.logger.info_exc(file=sys.stderr)
        try:
            server.quit()
        except Exception:
            pass
        return False


if __name__ == '__main__':
    logger.info("发送邮件开始")
    emailSend('600689 股票监控信息提醒')
    emailSendParameter(['600689', '600690', '600691'])