import datetime
from common.logger import logger
import time





def getTimestampAdd(dayNum=0, timeType="ms"):
    nowtimeIntn = time.time()
    t = nowtimeIntn
    if dayNum != 0:
        dayChg = (datetime.datetime.now() + datetime.timedelta(days=dayNum)).strftime("%Y-%m-%d %H:%M:%S")
        t = time.mktime(time.strptime(dayChg, "%Y-%m-%d %H:%M:%S"))

    if timeType == "s":
        t = int(round(nowtimeIntn))
    else:
        t = int(round(t * 1000))
    return t


def timeCalculate(time, dayNum=1):
    specified_date = datetime.date(time)
    # 默认将指定日期减去一天
    t = specified_date - datetime.timedelta(days=dayNum)

    return t


def getDateStr():
    now = datetime.datetime.now()
    dStr = str(now.strftime("%Y%m%d"))
    return dStr

def getDateStr_():
    now = datetime.datetime.now()
    dStr = str(now.strftime("%Y-%m-%d"))
    return dStr


def getTimeStr():
    now = datetime.datetime.now()
    dStr = now.strftime("%Y%m%d_%H%M%S")
    return dStr


def getSqlTimeStr(add=0):
    now = datetime.datetime.now()
    dStr = now.strftime("%Y:%m:%d %H:%M:%S")
    return dStr


def getSqlTimeStrAdd(addMin=0):
    now = datetime.datetime.now()
    new_time = now + datetime.timedelta(minutes=addMin)
    dStr = new_time.strftime("%Y:%m:%d %H:%M:%S")
    return dStr


def getTimeStrLine():
    now = datetime.datetime.now()
    dStr = now.strftime("%Y%m%d%H%M%S")
    return dStr


def getZoneTime():
    # 拼接标注时间
    now = datetime.datetime.now()
    zoneTime = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    zoneTime = str(zoneTime) + "+8:00"
    return zoneTime


def time_changer(time_):
    """
    2025-01-15 时间转化 20250115
    """
    time_ = time_.replace("-", "")
    return time_
if __name__ == '__main__':
    # pass
    # print(getTimestampAdd(1, "s"))
    # print(getTimestampAdd())
    # print(getZoneTime())
    # print(getTimestampAdd() + 100000)
    # print(getTimeStrLine())
    # print(getSqlTimeStrAdd(10))
    # print(type(getSqlTimeStr()))
    # account = "NetAgency" + getTimeStrLine()
    # print(account[-18:])
    # print(getTimeStr())
    # userName = ["14018171800", "1", "3"]
    # print(type(userName))

    # lbdmCode = '123456789'
    # len(lbdmCode)
    # logger.info(lbdmCode[:4])
    # print(getDateStr_())
    time = '2025-01-15'
    print(time_changer(time))