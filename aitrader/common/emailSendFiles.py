#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, make_msgid
from email.header import Header
import smtplib
import socket
import glob
from common.logger import logger
from common.readFile import ReadFile


# ============================================================
# 内部辅助
# ============================================================

def _load_email_config():
    """加载邮件 SMTP 配置，返回 (smtp_config_dict, full_yaml_data)"""
    yamlData = ReadFile.get_yamlAllPath("/config/emailConfig.yaml")
    emailCon = yamlData["emailService"]["oStMailCofig"]
    return emailCon, yamlData


def _get_task_receiver(task_id):
    """获取指定任务的收件人列表，不存在则回退到 default → 全局 receiver"""
    _, yamlData = _load_email_config()
    task_email_cfg = yamlData.get("taskEmail", {})
    cfg = task_email_cfg.get(task_id) or task_email_cfg.get("default", {})
    receiver = cfg.get("receiver", yamlData.get("receiver", ""))
    if isinstance(receiver, str):
        receiver = [r.strip() for r in receiver.split(",") if r.strip()]
    return receiver


def _close_server(server):
    try:
        server.quit()
    except Exception:
        pass


def _send_email_impl(receiver, subject, body_text, body_html=None):
    """底层 SMTP 发送（SSL），支持纯文本 + 可选 HTML"""
    emailCon, _ = _load_email_config()
    smtp_server = emailCon["MAIL_SERVER"]
    port = emailCon["MAIL_PROT"]
    sender_email = emailCon["MAIL_USERNAME"]
    password = emailCon["MAIL_PASSWORD"]

    print(f"[EMAIL] SMTP: {smtp_server}:{port}  sender={sender_email}  receivers={receiver}")

    if not password:
        print(f"[EMAIL] 失败: MAIL_PASSWORD 为空", file=sys.stderr)
        return False
    if not receiver:
        print(f"[EMAIL] 失败: receiver 为空", file=sys.stderr)
        return False

    # 构建邮件
    subtype = "alternative" if body_html else "mixed"
    msg = MIMEMultipart(subtype)
    msg["From"] = f"AI股票分析系统 <{sender_email}>"
    to_addrs = ", ".join(receiver) if isinstance(receiver, list) else receiver
    msg["To"] = to_addrs
    msg["Subject"] = Header(subject, "utf-8")
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender_email.split("@")[-1])
    msg["X-Mailer"] = "AIStockAgent"
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    # 连接 SMTP
    print(f"[EMAIL] 连接 SMTP {smtp_server}:{port} (timeout=30s)...")
    try:
        server = smtplib.SMTP_SSL(smtp_server, port, timeout=30)
    except socket.gaierror as e:
        print(f"[EMAIL] 失败: DNS 解析失败 {smtp_server}: {e}", file=sys.stderr)
        return False
    except socket.timeout as e:
        print(f"[EMAIL] 失败: 连接超时 {smtp_server}:{port}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[EMAIL] 失败: 连接异常 {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

    print(f"[EMAIL] SMTP 连接成功, 登录并发送...")
    try:
        server.login(sender_email, password)
        raw = msg.as_string()
        server.sendmail(sender_email, receiver, raw)
        _close_server(server)
        logger.info(f"[EMAIL] 发送成功 subject={subject} receivers={receiver}")
        print(f"[EMAIL] ====== 邮件发送成功 ======")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL] 失败: SMTP 认证失败: {e}", file=sys.stderr)
        _close_server(server)
        return False
    except Exception as e:
        print(f"[EMAIL] 失败: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        _close_server(server)
        return False


# ============================================================
# 公开接口
# ============================================================

def send_task_email(task_id, content, title=None, body_html=None, receiver=None):
    """
    通用定时任务邮件发送。

    收件人优先级:
      1. receiver 参数（显式传入，用于 UI 配置的多人发送）
      2. emailConfig.yaml 的 taskEmail.<task_id>.receiver
      3. emailConfig.yaml 的 taskEmail.default.receiver
      4. emailConfig.yaml 的 receiver（全局配置）

    参数:
        task_id:   任务标识 (如 "xunlong", "check_notice", "check_house")
        content:   邮件纯文本正文
        title:     邮件标题
        body_html: 可选 HTML 正文
        receiver:  可选，直接指定收件人（逗号分隔字符串或列表），覆盖配置文件
    返回:
        True / False
    """
    print(f"[EMAIL] ====== 任务邮件 task_id={task_id} ======")
    print(f"[EMAIL] 标题: {title}")
    print(f"[EMAIL] 正文: {len(content or '')} 字符, HTML: {'是' if body_html else '否'}")

    try:
        if receiver:
            if isinstance(receiver, str):
                receiver = [r.strip() for r in receiver.split(",") if r.strip()]
            print(f"[EMAIL] 收件人(来自参数): {receiver}")
        else:
            receiver = _get_task_receiver(task_id)
            print(f"[EMAIL] 收件人(来自 taskEmail.{task_id}): {receiver}")
    except Exception as e:
        print(f"[EMAIL] 读取任务邮件配置失败: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

    return _send_email_impl(receiver, title, content, body_html)


def emailSendContent(content, title='公告变化提醒'):
    """向后兼容：使用全局 receiver 发送纯文本邮件"""
    print(f"[EMAIL] ====== 发送邮件 ======")
    print(f"[EMAIL] 标题: {title}, 正文: {len(content)} 字符")

    _, yamlData = _load_email_config()
    receiver = yamlData.get("receiver", "")
    if isinstance(receiver, str):
        receiver = [r.strip() for r in receiver.split(",") if r.strip()]

    return _send_email_impl(receiver, title, content)


def emailSend(title='股市监控信息提醒'):
    logger.info("发送邮件开始...")
    yamlData = ReadFile.get_yamlAllPath("/config/emailConfig.yaml")
    emailCon = yamlData["emailService"]["oStMailCofig"]
    reportPath = yamlData["reportPath"]
    receiver = yamlData["receiver"]
    logger.info(receiver)

    smtp_server = emailCon["MAIL_SERVER"]
    port = emailCon["MAIL_PROT"]
    sender_email = emailCon["MAIL_USERNAME"]
    password = emailCon["MAIL_PASSWORD"]

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(receiver) if isinstance(receiver, list) else receiver
    msg['Subject'] = title

    body = '您好，这是股市监控信息提醒，系统邮件请勿回复，谢谢！'
    msg.attach(MIMEText(body, 'plain'))

    pattern = '*.html'
    directory = ReadFile.getProjectPath() + reportPath
    search_path = os.path.join(directory, pattern).replace("\\", '/')
    files = glob.glob(search_path)
    try:
        for file in files:
            logger.info(f"file:{file}")
            with open(file, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(file)}")
                msg.attach(part)

        with smtplib.SMTP_SSL(smtp_server, port, timeout=30) as server:
            server.login(sender_email, password)
            text = msg.as_string()
            server.sendmail(sender_email, receiver, text)
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


def emailSendParameter(stock_list, title='今日推荐票信息'):
    logger.info("发送邮件开始...")
    yamlData = ReadFile.get_yamlAllPath("/config/emailConfig.yaml")
    emailCon = yamlData["emailService"]["oStMailCofig"]
    reportPath = yamlData["reportPath"]
    receiver = yamlData["receiver"]

    smtp_server = emailCon["MAIL_SERVER"]
    port = emailCon["MAIL_PROT"]
    sender_email = emailCon["MAIL_USERNAME"]
    password = emailCon["MAIL_PASSWORD"]

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(receiver) if isinstance(receiver, list) else receiver
    msg['Subject'] = title

    body = f'您好，这是今日推荐票信息：{stock_list}，\n \n \n 系统邮件请勿回复，谢谢！'
    msg.attach(MIMEText(body, 'plain'))

    pattern = '*.html'
    directory = ReadFile.getProjectPath() + reportPath
    search_path = os.path.join(directory, pattern).replace("\\", '/')
    files = glob.glob(search_path)
    try:
        for file in files:
            logger.info(f"file:{file}")
            with open(file, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(file)}")
                msg.attach(part)

        with smtplib.SMTP_SSL(smtp_server, port, timeout=30) as server:
            server.login(sender_email, password)
            text = msg.as_string()
            server.sendmail(sender_email, receiver, text)
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


if __name__ == '__main__':
    print("发送邮件开始")
    emailSend('600689 股票监控信息提醒')
    emailSendParameter(['600689', '600690', '600691'])
