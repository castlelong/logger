#!/usr/bin/env python
# !coding: utf-8

# 自动转换日志格式为json格式,按受参数为项目名，第二个参数可接日志文件名，第三个参数为文件偏移量 方便处理历史日志，需要设置项目路径等信息
# 1. 直接项目名启动方法 convertjson.py urm
# 2. 处理历史日志启动方法 convertjson.py urm  /data/urm/logs/log4j.log_20170112.log 1122
# Author: chenyanghong
# Version: 1.0
# Date： 2017-1-13
# E-mail: 32415397@qq.com
# -------------------------------------------
# change user: longyucen
# change date:2017-10-09
# Version: 1.1
# chnage message:
# 将所有文件归集到工程目录下
import re
import sys
import os
import shutil
import logging.config
import time, datetime

BASE_DIR = os.path.dirname(__file__)  # 程序目录

logging.config.fileConfig(os.path.join(BASE_DIR, "logger.conf"))  # 日志配制文件
logger = logging.getLogger("ZP")  # 取日志标签，可选为development,production


def joinjson(message):  # 生成json格式
    global jsonfile, projectname
    relist = re.split(' ', message)
    zplist_1 = relist[0].split(']')[0]
    zplist = zplist_1.split(':')
    zp = str(zplist[1])
    master_zp = zp.split('-')[0]
    atime = time.strftime("%Y-%m-%d", time.localtime()) + "-" + relist[0].split(']')[1]
    index = str(relist[1]).replace('[', '').replace(']', '')
    level = str(relist[3])
    modules = projectname
    specifics = ""
    for i in range(5, len(relist)):
        specifics += str(relist[i])
    specifics = re.sub('\s|"', '', specifics)  # 替换制表符，双引号
    jsonstr = '{"master_zp":"%s","zp":"%s","time":"%s","index":"%s","level":"%s","specifics":"%s","modules":"%s"}' % (
        master_zp, zp, atime, index, level, specifics, modules)
    f = open(jsonfile, 'ab+')
    f.writelines(jsonstr + "\n")
    f.close()


def checknewlog():
    if os.path.exists(jsonfile):
        logtime = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(jsonfile)))
        if logtime != time.strftime('%Y-%m-%d'):
            try:
                os.rename(jsonfile, jsonfile + '_' + logtime)
            except:
                pass


def joinmessage(data):  # 通过列表拼接字符串
    global templist
    if len(templist) == 1:  # 如果只存在一个元素，直接调用json生成函数
        joinjson(str(templist[0]))
    else:
        position = 0
        message = ""
        for i in range(len(templist)):  # 取出以^开头的行
            if re.search('^\[', templist[i]):
                position = int(i)
                message = str(templist[i])
                break
        for j in range(len(templist)):  # 拼接字符串
            if j != position:
                message = message + '====' + str(templist[j]) + '===='
        joinjson(message)
    templist = [data]  # 清空列表


def checklist():  # 检测列表中是否有^开头的字符串
    global templist
    if len(templist) == 0:
        return 0
    for i in templist:
        if re.search('^\[', str(i)):
            return 1
    return 0


def handler(message):  # 把新读到的日志加入列表
    global templist
    if re.search('^\[', message):
        relist = re.split(' ', message)  # 如果开头为[但是列长度不够
        # [xx] [128] INFO 2017-03-22 13:45:15 xx  这种日志格式
        if len(relist) >= 6:  #
            result = checklist()  # 检测列表中元素是否有^开头的字符串
            if result:
                joinmessage(message)  # 处理新读到的日志
            else:
                templist.append(message)  # 把新读到的日志加入列表
        else:
            templist.append(message)  # 把新读到的日志加入列表
    else:
        templist.append(message)  # 把新读到的日志加入列表


def checkpos():  # 检查位置文件信息，如果更改时间不是当天就备份出来
    global pos
    # print(pos, 'posaaaa')
    if os.path.exists(pos):
        postime = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(pos)))
        if postime != time.strftime('%Y-%m-%d'):
            try:
                os.rename(pos, pos + '_' + postime)
            except:
                pass


def checkoldlog(filename):  # 取历史日志最大的偏移量跟判断文件是否存在
    if os.path.exists(filename):
        try:
            f = open(filename, 'r')
            f.seek(0, 2)
            return f.tell()  # 返回文件最大位置
        except:
            return 0
    else:
        return 0


def checklogfilehandler():  # 检测前一天的日志是否已经处理完， 返回值为0代表没有读完，返回值为1代表已读完
    global logfile, projectname
    yestday = str(datetime.date.today() - datetime.timedelta(days=1)).replace('-', '')  # 获取昨天日期
    ylogfile = "%s_%s.log" % (logfile, yestday)  # 前一天的日志文件名
    if os.path.exists(ylogfile):
        try:
            fylogfile = open(ylogfile, 'r+')
            fylogfile.seek(0, 2)  # 定位到文件尾
            fyoff = fylogfile.tell()  # 前一天的日志文件的最大偏移量
            fylogfile.close()
            fpos = open(pos)  # 打开目前文件偏移量记录文件
            cpos = int(fpos.readline().strip('\n'))  # 读出偏移量
            fpos.close()  # 关闭文件
            if int(fyoff) == cpos:  # 如果相等，说明已经全部读完
                return 1
            else:
                return 0
        except Exception, e:
            logger.error(u"项目%s检测前一天日志读取情况失败！，错误代码%s" % (projectname, e))
            return 0
    else:
        return 0


def readnew():  # 处理时时日志文件
    global logfile, projectname, jsonfile, pos, pjpath, newlogpath
    newlogpath = "%s/%s" % (logpath, projectname)
    if not os.path.exists(newlogpath):
        try:
            os.makedirs(newlogpath)
        except:
            logger.error(u"错误：创建%s 目录失败" % newlogpath)
            sys.exit(1)
    checkpos()  # 检测位置文件信息

    if os.path.exists(pos):  # 如果位置信息文件存在就读出位置信息
        f = open(pos, 'r')
        fileseek = f.readline().strip('\n')
        f.close()
    else:  # 如果不存在，从文件最后开始读
        fileseek = 0
    f = open(logfile, 'r')  # 以只读方式打开日志文件
    logger.info(u"开始读取项目%s日志文件%s" % (projectname, logfile))
    try:
        if fileseek:  # 如果fileseek为真
            f.seek(int(fileseek))  # 定位文件位置
        else:
            f.seek(int(fileseek), 2)  # 定位最后位置
    except:
        print 'get position error'
        logger.error(u'项目%s获取日志位置失败' % projectname)
        sys.exit(1)

    while True:
        try:
            finode = open(finodefile, 'r+')   # 打开inode节点记录文件
            oldinode = int(finode.readline().strip('\n'))  # 读取inode节点记录文件中的节点位置
            print(oldinode, 'oldinode')
            finode.close()
        except Exception, e:
            logger.error(u"项目%s读取inode记录文件出错，文件名：%s, 错误代码:%s" % (projectname, finodefile, e))
            sys.exit(1)
        try:
            currentinode = int(os.stat(logfile).st_ino)  # 读取现有文件的inode信息
            print(currentinode, 'currentinode')
        except Exception, e:
            logger.error(u"项目%s读取日志文件%s文件inode信息出错，错误代码:%s" % (projectname, logfile, e))
            pass
        if currentinode != oldinode:  # 如果inode节点改变了，说明文件改变了
            if checklogfilehandler:  # 当前一天的日志处理完成后才进行重新打开日志文件处理
                f.close()
                try:
                    shutil.copyfile(jsonfile, jsonfile + '_' + time.strftime('%Y%m%d') + '.log')  # 复制文件
                    fjson = open(jsonfile, 'wb')  # 清空文件内存
                    time.sleep(1)
                    fjson.close()
                    time.sleep(1)
                except:
                    currentdate = time.strftime('%Y-%m-%d %H:%M:%S')
                    logger.error(u"%s文件在%s改名失败" % (jsonfile, currentdate))
                time.sleep(2)
                try:
                    f = open(logfile, 'r')  # 以只读方式打开日志文件
                    f.seek(0)  # 定位文件开头
                except Exception, e:
                    logger.error(u"打开项目%s日志文件%s失败，错误代码:%s" % (projectname, logfile, e))
                    sys.exit(1)
        message = f.readline().strip('\n')  # 读取一行日志
        print message
        if message:
            handler(message)
            if os.path.exists(pos):  # 判断位置文件是否存在，如存在就使用rb+方式打开，不然使用wb+会报错
                fp = open(pos, 'rb+')  # 读出有效数据才写位置信息
                fp.write(str(f.tell()))
                fp.close()
            else:
                fp = open(pos, 'wb+')  # 读出有效数据才写位置信息
                fp.write(str(f.tell()))
                fp.close()
            time.sleep(0.01)  # 休息0.01秒，降低cpu使用
        else:
            time.sleep(1)  # 如果读到文件尾，使进程睡眠一秒，降低CPU使用


def readold(oldlogfile, maxseek, currentseek):  # 处理历史日志文件
    global newlogpath, jsonfile, projectname
    newlogpath = "%s/%s" % (newlogpath, projectname)
    if not os.path.exists(newlogpath):
        try:
            os.makedirs(newlogpath)
        except:
            logger.error(u"错误：创建%s 目录失败" % newlogpath)
            sys.exit(1)
    jsonfile = newlogpath + '/' + jsonfile
    f = open(oldlogfile, 'r')  # 以只读方式打开日志文件
    try:
        f.seek(currentseek)  # 定位文件开头
    except Exception, e:
        print 'get position error'
        logger.error(u"错误：项目%s日志文件位置信息获取失败,错误代码：%s" % (projectname, e))
        sys.exit(1)
    while True:
        message = f.readline().strip('\n')  # 读取一行日志
        if message:
            handler(message)
            time.sleep(0.01)  # 休息0.01秒，降低cpu使用
        else:
            if f.tell() == maxseek:
                handler('[aa] a a a a')  # 把最后一台全刷到文件中
                logger.error(u"恭喜：历史日志文件%s已处理完毕" % oldlogfile)
                sys.exit(0)
            time.sleep(1)  # 如果读到文件尾，使进程睡眠一秒，降低CPU使用


if __name__ == "__main__":

    # 全局变量区
    pjpath = "/home/logs/" + sys.argv[1]
    logpath = "/home/logs/exchange"
    pos = 'pos.txt'  # 日志文件位置信息存放文件
    logfile = ''  # 日志文件
    jsonfile = 'newlog.log'  # 生成的json格式文件
    templist = []  # 公用列表，用于临时存储日志
    finodefile = 'inode.txt'  # 文件inode文件，用于比较日志文件是否有截转
    argscount = len(sys.argv)  # 获取参数列表长度
    if argscount == 1:
        print "错误：运行方式%s 项目名" % (sys.argv[0])
        logger.error(u"错误：运行方式%s 项目名" % (sys.argv[0]))
        sys.exit(1)

    if argscount == 3:
        print "错误：运行方式%s 项目名 日志名 偏移量" % (sys.argv[0])
        logger.error(u"错误：运行方式%s 项目名 日志名 偏移量" % (sys.argv[0]))
        sys.exit(1)

    if argscount >= 4:
        if not str(sys.argv[3]).isdigit():  # 如果偏移量不为数字即退出
            print "错误：第三个参数请填入正确的数字，如果文件全部要读请填0"
            logger.error(u"错误：第三个参数请填入正确的数字，如果文件全部要读请填0")
            sys.exit(1)
        result = checkoldlog(sys.argv[2])  # 如果文件存在，返回文件最大的偏移量，否则返回0
        if not result:
            print "错误：日志文件%s不存在" % sys.argv[2]
            logger.error(u"错误：日志文件%s不存在" % sys.argv[2])
            sys.exit(1)

    if argscount < 4:
        projectname = str(sys.argv[1])
        projeclogname = str(sys.argv[1]) + "-" + time.strftime("%Y-%m-%d", time.localtime())
        print(projectname)
        logfile = "%s/%s.0.log" % (pjpath, projeclogname)
        # print(logfile)
        finodefile = "%s/%s/%s" % (logpath, projectname, finodefile)
        # print(finodefile)
        pos = "%s/%s/%s" % (logpath, projectname, pos)
        # print(pos)
        jsonfile = "%s/%s/%s" % (logpath, projectname, jsonfile)
        # print(jsonfile)
        while True:
            if os.path.exists(logfile):  # 如果项目日志文件存在
                try:
                    finode = open(finodefile, 'wb+')
                    finode.write(str(os.stat(logfile).st_ino))  # 把文件inode写入inode记录文件
                    finode.close()
                except Exception, e:
                    logger.error(u"项目%s写入inode文件失败，inode文件名：%s，错误代码：%s" %(projectname, finodefile, e))
                break
            time.sleep(5)
        readnew()  # 处理时时日志
    else:
        if result < int(sys.argv[3]):
            print "错误：开始读位置不能大于文件最大偏移量"
            logger.error(u"错误：开始读位置不能大于文件最大偏移量")
            sys.exit(1)
        projectname = sys.argv[1]
        oldlogfile = sys.argv[2]
        oldfileseek = int(sys.argv[3])
        readold(oldlogfile, result, oldfileseek)  # 处理历史日志,传入三个参数,第一个日志文件名，第二个文件总偏移量，第三个为从哪个位置开始读