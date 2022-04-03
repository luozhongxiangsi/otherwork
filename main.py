import datetime
import re
import traceback

import pandas as pd
import requests
from bs4 import BeautifulSoup

proxies = ""

headers = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664."
                  "45 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9"
}


def update_header(url: str):
    """
    更新headers
    :param url:
    :return:
    """
    #  Host": "www.pkulaw.com",
    host = ""
    headers.update({"Host": host})
    # Referer": "https://www.pkulaw.com/case/",
    referer = ""
    headers.update({"Referer": referer})
    cookies = ""
    headers.update({"Cookie": cookies})


def casenum_get(file_path):
    """
    读取需要爬取的案号
    :param file_path: 案号文件路径
    :return: [list] 所有的案号
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        case_list = f.readlines()
    return case_list


def results_filter(results, casenum, appeal):
    """
    多结果筛选算法
    根据案号搜索结果可能多个，需要获取多个中有效的一个
    参数： results    包含多个返回结果
    casenum    目标案号
    appeal      是否为二审
    :param results:
    :param casenum:
    :param appeal:
    :return:
    """
    index = -1
    if len(results) <= 0:
        return index

    # 记录每个索引权重，0表示无用，1表示重要，2表示次要
    res_list = [0] * len(results)

    # 预处理casenum，删除换行符，准备英文版
    casenum = casenum.replace('\r', '').replace('\n', '')
    casenum2 = casenum.replace("（", "(").replace("）", ")").replace('\r', '').replace('\n', '')

    # 排列出权重
    for cnt in range(0, len(results)):
        # 获取每条结果的相关信息，文字版
        soup = BeautifulSoup(str(results[cnt]), 'html5lib')
        results[cnt] = soup.get_text()

        print("results=", str(results[cnt]).split("/"))
        # 获取具体案号信息（主要用于一审）
        infos = str(results[cnt]).split("/")
        res_cn = ""
        for info in infos:
            if info.find(casenum) >= 0 or info.find(casenum2) >= 0:
                res_cn = info.strip()

        # 处理二审情况
        if appeal:
            if str(results[cnt]).find(casenum) >= 0 or str(results[cnt]).find(casenum2) >= 0:
                res_list[cnt] = 0
            elif str(results[cnt]).find("判决书") >= 0:
                res_list[cnt] = 1
            else:
                res_list[cnt] = 2
        # 处理一审情况
        else:
            if casenum != res_cn and casenum2 != res_cn:
                res_list[cnt] = 0
            elif str(results[cnt]).find("判决书") >= 0:
                res_list[cnt] = 1
            else:
                res_list[cnt] = 2

    # 获取最优权重
    for cnt in range(0, len(res_list)):
        if res_list[cnt] == 1:
            index = cnt
            break
        elif index < 0 and res_list[cnt] == 2:
            index = cnt

    return index


def url_get_bycasenum(case_num: str, web_head_url: str = "https://www.pkulaw.com/case/pfnl") -> str:
    """
    根据案号查询对应案件的url
    此函数只能用于一审
    :param web_head_url: 目标内型的url
    :param case_num: 案号
    :return: 一审url
    """

    log = "\033[0;31m案号获取URL：\033[0m"
    # 查询一审案件请求体
    d = {
        "Menu": "case",
        "Keywords": case_num,
        "PreKeywords": case_num,
        "SearchKeywordType": "Code",
        "MatchType": "Exact",
        "RangeType": "Piece",
        "Library": "pfnl",
        "ClassFlag": "pfnl",
        "QuerySearchCondition": "Code + 0",
        "QueryOnClick": False,
        "AfterSearch": True,
        "RequestFrom": "btnSearch",
        "PreviousLib": "pfnl",
        "IsSynonymSearch": "true",
        "ClassCodeKey": ",,,,,,,,,,",
        "RecordShowType": "List",
        "X-Requested-With": "XMLHttpRequest"
    }
    target_url = ""
    try:
        # 搜索页面POST请求
        res = requests.post(web_head_url, data=d, headers=headers, proxies=proxies)
        # print(res.status_code)
        # 获取错误
        if res.status_code != 200:
            print(log, "POST请求失败")
            return ""
        # 解析获取页面
        # 解析页面中目标所在div标签
        soup = BeautifulSoup(res.text, 'html5lib')

        badcontent = str(soup.find_all("div", "search-no-content"))
        if len(badcontent) > 10:
            print(log, "搜索未找到", len(badcontent))
            return ""

        # 处理多个结果
        results = soup.find_all("div", "related-info")
        index = 0
        # 进行数据过滤
        index = results_filter(results, case_num, False)

        if index < 0:
            print(log, "未查询到正确结果")
            return ""

        # print("index=", index)
        badcontent = str(soup.find_all("div", "list-title")[index])
        # print(badcontent)
        if len(badcontent) <= 0:
            print(log, "div标签不存在")
            return ""

        # 解析div中a标签
        soup = BeautifulSoup(badcontent, 'html5lib')
        badcontent = str(soup.find_all("a")[0])
        # print(badcontent)
        if len(badcontent) <= 0:
            print(log, "a标签不存在")
            return ""

        # 解析目标url
        aim_url = badcontent.split('\"')
        if len(aim_url) < 3 or len(aim_url[3]) <= 0:
            print(log, "URL不存在")
            return ""
        # print(aim_url[3])
        target_url = "https://www.pkulaw.com" + aim_url[3]
    except Exception as e:
        print(log, e)
        traceback.print_exc()
    finally:
        return target_url


def url_check_bycasenum(case_num: str, target_url: str = "https://www.pkulaw.com/case/pfnl") -> str:
    """
    查询案号是否有不服上诉
    根据"不服" + 案号搜索记录
    :param target_url:
    :param case_num: 案号
    :return:
    """
    # 预处理搜索内容
    search = "不服 " + case_num
    # search_key = "上诉 " + case_num
    log = "\033[0;31m案号上诉检查URL：\033[0m"
    ret_url = ""
    url = target_url
    d = {
        "Menu": "case",
        "Keywords": search,
        # "PreKeywords": search_key,
        "SearchKeywordType": "TrialAfter",
        "MatchType": "Exact",
        "RangeType": "Piece",
        "Library": "pfnl",
        "ClassFlag": "pfnl",
        "QuerySearchCondition": "TrialAfter + 0",
        "QueryOnClick": False,
        "AfterSearch": True,
        "RequestFrom": "btnSearch",
        "PreviousLib": "pfnl",
        "IsSynonymSearch": "true",
        "ClassCodeKey": ",,,,,,,,,,",
        "RecordShowType": "List",
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        # 搜索页面POST请求
        res = requests.post(url, data=d, headers=headers, proxies=proxies)
        # print(res.status_code)
        # 获取错误
        if res.status_code != 200:
            print(log, "POST请求失败")
            return ""
        # 解析获取页面
        # 解析页面中目标所在div标签
        soup = BeautifulSoup(res.text, 'html5lib')

        badcontent = str(soup.find_all("div", "search-no-content"))
        if len(badcontent) > 10:
            print(log, "搜索未找到", len(badcontent))
            return ""

        # 处理多个结果
        results = soup.find_all("div", "related-info")
        index = 0

        # 进行数据过滤
        index = results_filter(results, case_num, True)

        if index < 0:
            print(log, "未查询到正确结果")
            return ""

        # print("index=", index)
        badcontent = str(soup.find_all("div", "list-title")[index])
        # print(badcontent)
        if len(badcontent) <= 0:
            print(log, "div标签不存在")
            return ""

        # 解析div中a标签
        soup = BeautifulSoup(badcontent, 'html5lib')
        badcontent = str(soup.find_all("a")[0])
        # print(badcontent)
        if len(badcontent) <= 0:
            print(log, "a标签不存在")
            return ""

        # 解析目标url
        aim_url = badcontent.split('\"')
        if len(aim_url) < 3 or len(aim_url[3]) <= 0:
            print(log, "URL不存在")
            return ""
        # print(aim_url[3])
        ret_url = "https://www.pkulaw.com" + aim_url[3]
        return ret_url
    except Exception as e:
        print(log, e)
        ret_url = ""
    finally:
        return ret_url


def get_caseinfo(text, infotype):
    """
    获取信息
    通过下载文本获取案件信息(审理法官、文书类型、公开类型、审理程序、案号等)
    :param text:
    :param infotype:
    :return:
    """
    log = "\033[0;31m案件信息解析：\033[0m"
    ret_caseinfo = ""
    try:
        # 获取案件审理法官
        soup = BeautifulSoup(text, 'html5lib')
        taglist = soup.find_all("div", "box")
        # 查询案件信息
        for tag in taglist:
            # 获取信息
            if str(tag).find(infotype) >= 0:
                # print(str(tag))
                soup = BeautifulSoup(str(tag), 'html5lib')
                badcontent = str(soup.get_text())
                # print(badcontent)
                ret_caseinfo = badcontent

        # 解析到精确信息
        if ret_caseinfo != "":
            info_list = ret_caseinfo.split("：")
            ret_caseinfo = re.sub('\s+', ',',
                                  info_list[-1].replace('\r', '').replace('\n', '').replace('\x0b', ' ')).strip(
                ',').strip()
        else:
            print(log, "获取案件信息失败")

        return ret_caseinfo
    except Exception as e:
        print(log, e)
        ret_caseinfo = ""
    finally:
        return ret_caseinfo


def down_file(text: str):
    """
    解析网页
    :param text:
    :return:
    """
    log = "\033[0;31m下载正文：\033[0m"
    ret_content = ""

    try:
        # 获取案件原文
        soup = BeautifulSoup(text, 'html5lib')
        badcontent = str(soup.find_all("div", id="divFullText")[0])
        # print(badcontent)
        if len(badcontent) <= 0:
            print(log, "div标签不存在")
            return ""

        soup = BeautifulSoup(badcontent, 'html5lib')
        ret_content = str(soup.get_text())
        # print(ret_context)
        if len(ret_content) <= 0:
            print(log, "正文不存在")
            return ""

        # 长时间下载将出现部分正文被省略
        if re.search(r"\.\.\.\.\.\.", ret_content) is not None:
            print(ret_content)
            print(log, "正文不完整")
            # return ""

        return ret_content
    except Exception as e:
        print(log, e)
        ret_content = ""
    finally:
        return ret_content
    pass


# 获取上诉结果
def appeal_result(text):
    log = "\033[0;31m上诉结果：\033[0m"
    ret_content = ""

    try:
        # 获取案件原文
        soup = BeautifulSoup(text, 'html5lib')
        badcontent = str(soup.find_all("div", id="divFullText")[0])
        # print(badcontent)
        if len(badcontent) <= 0:
            print(log, "div标签不存在")
            return ""

        soup = BeautifulSoup(badcontent, 'html5lib')
        ret_content = str(soup.get_text())
        # print(ret_context)
        if len(ret_content) <= 0:
            print(log, "正文不存在")
            return ""

        # 长时间下载将出现部分正文被省略
        if re.search(r"\.\.\.\.\.\.", ret_content) is not None:
            print(ret_content)
            print(log, "正文不完整")
            # return ""

        # 根据"审判长"和<br/>来查询正文倒数5行文本
        if re.search(r"<br/>.{0,2}审.{0,5}判.{0,5}长", badcontent) is not None:
            res = re.search(r"<br/>.{0,2}审.{0,5}判.{0,5}长", badcontent)
            print("查询结果(审判长)", res.span())
        elif re.search(r"<br/>.{0,2}审.{0,5}判.{0,5}员", badcontent) is not None:
            res = re.search(r"<br/>.{0,2}审.{0,5}判.{0,5}员", badcontent)
            print("查询结果(审判员)", res.span())
        else:
            print(log, "无法查询审判结果")
            return ""

        # 处理倒数几行
        if res != None:
            content = badcontent[:res.span()[0]]
            lines = content.split("<br/>")
            revise = 0
            for j in range(-1, -10, -1):
                # 判断文本内容（”驳回上诉“和”维持原判“），并修改结果
                if abs(j) > len(lines):
                    revise = 1
                    break
                if lines[j].find("驳回上诉") >= 0 or lines[j].find("维持原判") >= 0:
                    revise = 0
                    break
                else:
                    revise = 1

            if revise == 1:
                ret_content = "修改判决"
            else:
                ret_content = "驳回上诉 维持原判"
        else:
            return ""

        return ret_content
    except Exception as e:
        print(log, e)
        ret_content = ""
    finally:
        return ret_content
    pass


def get_strtime(text: str):
    """
    获取文字中日期信息
    :param text:
    :return:
    """
    # 预处理文本文字
    text = text.replace("年", "-").replace("月", "-").replace("日", " ").replace("/", "-").strip()
    text = re.sub("\s+", " ", text)
    t = ""
    # 正则表达式
    regex_list = [
        # 2013年8月15日 22:46:21
        r"(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})",
        # "2013年8月15日 22:46"
        r"(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2})",
        # "2014年5月11日"
        r"(\d{4}-\d{1,2}-\d{1,2})",
        # "2014年5月"
        # "(\d{4}-\d{1,2})",
    ]

    # 正则表达式匹配
    for regex in regex_list:
        t = re.search(regex, text)
        if t:
            t = t.group(1)
            return t
        else:
            t = ""
            print("没有获取到有效日期")
    return t


def get_proxy_ip():
    """
    获取代理池中的代理IP
    :return:
    """
    global proxies
    req = requests.get("http://localhost:5555/random")
    ip_port: str = req.text.strip()
    proxies = {'http': 'http://' + ip_port}
    return proxies


if __name__ == "__main__":
    path = r"./案号.txt"
    case_nums = casenum_get(path)

    excel_path = r"/Users/nianfouyi/Desktop/兼职/result_sort.xlsx"
    df = pd.read_excel(r"/Users/nianfouyi/Desktop/兼职/result_sort.xlsx")

    # 获取已完成的案号，并转化为列表
    cols = df["一审案号"]
    col_list = cols.values.tolist()

    # 错误案号记录
    err_fd = open("./err_casenum.txt", "a+")

    # 重试次数
    retry = 0

    for i in range(0, len(case_nums)):
        # 显示目前运行索引
        print("运行索引：", i, "  案号：", case_nums[i])
        # 检查案号是否已经处理完成
        flag = False
        for col in col_list:
            if case_nums[i] == str(col):
                flag = True
                break
        # 处理完成则跳过
        if flag:
            continue

        # 从代理池获取代理IP
        proxy_ip = get_proxy_ip()

        # 对未处理的案号进行处理

        # 获取案号URL
        aim_url = url_get_bycasenum(case_nums[i])
        if aim_url is None:
            aim_url = url_get_bycasenum(case_nums[i])
        if aim_url == "" or aim_url == "搜索未找到":
            print("案号URL获取异常")
            err_fd.write(case_nums[i])
            retry += 1
            # 重试机制
            if retry > 50:
                break
            continue

        print("aim_url=", aim_url)

        # 获取url网页
        try:
            ret = requests.get(aim_url, headers=headers, proxies=proxies)
            # print(ret.text)
        except Exception as e:
            # 异常重试机制
            proxies = get_proxy_ip()
            ret = requests.get(aim_url, headers=headers, proxies=proxies)

        # 获取案件信息***
        infotypes = ["审理法官", "文书类型", "公开类型", "审理程序"]
        caseinfos = []
        for t in infotypes:
            caseinfos.append(get_caseinfo(ret.text, t))
        print("caseinfos=", caseinfos)

        # 解析错误停止
        err = 0
        for info in caseinfos:
            if info == "":
                err += 1

        # 解析错误处理
        if err > 3:
            retry += 1
            # 重试机制
            if retry > 3:
                break
            continue

        retry = 0

        # 获取案件原文
        content = down_file(ret.text)
        if content == "":
            print("案件原文获取异常")
            err_fd.write(case_nums[i])
            continue
        print("案件原文=", content)
        # 获取立案日期***
        case_date = ""
        con_list = content.split('。')
        for con in con_list:
            # 立案或受理中的日期为立案日期
            if con.find("立案") >= 0 or con.find("受理") >= 0:
                case_date = get_strtime(con)
                print("立案|受理：", case_date)
                break
            # 提起、提出或起诉中日期需要加7天为立案日期
            if con.find("提起") >= 0 or con.find("提出") >= 0 or con.find("起诉") >= 0:
                case_date = get_strtime(con)
                if str(case_date) != "":
                    # 将日期字符串转成datetime格式
                    date = datetime.datetime.strptime(case_date, "%Y-%m-%d")
                    # 将日期加7天
                    date += datetime.timedelta(days=7)
                    print(date)
                    # 将日期转换会字符串
                    case_date = date.strftime("%Y-%m-%d")
                    print("提起|提出|起诉：", case_date)
                break

        # 获取案号是否有上诉
        try:
            appeal_url = url_check_bycasenum(case_nums[i])
        except Exception as e:
            # 异常重试机制
            proxies = get_proxy_ip()
            appeal_url = url_check_bycasenum(case_nums[i])
        print("appeal_url=", appeal_url)

        # 有上诉处理
        # 上诉结果***
        appeal = 0
        # 改判结果***
        revise = 0
        # 二审案号***
        sec_casenum = 0
        if appeal_url != "":
            appeal = 1
            # 获取上诉url网页
            try:
                ret = requests.get(appeal_url, headers=headers, proxies=proxies)
                # print(ret.text)
            except Exception as e:
                # 异常重试机制
                proxies = get_proxy_ip()
                ret = requests.get(appeal_url, headers=headers, proxies=proxies)

            # 获取二审案号
            sec_casenum = get_caseinfo(ret.text, "案 号")
            if sec_casenum == "":
                print("上诉案号获取异常")
                err_fd.write(case_nums[i])
                continue
            print("二审案号：", sec_casenum)

            # 获取二审结果
            content = appeal_result(ret.text)
            if content == "":
                print("上诉案号原文获取异常")
                err_fd.write(case_nums[i])
                continue
            print("二审案件原文=", content)
            # 判断是否改判
            revise = 0
            if content.find("驳回上诉") >= 0 or content.find("维持原判") >= 0:
                revise = 0
            else:
                revise = 1

        print("是否上诉：", appeal)
        print("上诉结果：", revise)

        # 写入案号
        df.loc[i, "一审案号"] = case_nums[i]

        # 写入案件信息
        for index in range(len(caseinfos)):
            df.loc[i, infotypes[index]] = caseinfos[index]

        # 写入立案日期
        if case_date != "":
            df.loc[i, "立案时间"] = case_date

        # 判断是否有上诉
        df.loc[i, "是否上诉(1/0)"] = appeal
        if appeal == 1:
            df.loc[i, "二审案号(没上诉的不用填)"] = sec_casenum
            df.loc[i, "二审是否改判(0/1，没上诉的不用填)"] = revise
        else:
            df.loc[i, "二审案号(没上诉的不用填)"] = ""
            df.loc[i, "二审是否改判(0/1，没上诉的不用填)"] = ""

        # 保存数据，index=False表示输出的文件不增加新的第一列作为index
        df.to_excel(excel_path, index=False)

        # 刷新写入文件
        err_fd.flush()
