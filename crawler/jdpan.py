import requests

# 禁用 urllib3 的 SSL 警告
import urllib3

def fetch_files(folder_uuid, owner=None, page=1):
    url = 'http://pan.jd.com/team/resource/page'
    headers = {
        # 根据你的 cURL 命令中的请求头信息填写
        # ...
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': 'jd.erp.lang=zh_CN; jdd69fo72b8lfeoe=YG5NQPG2DC3UUSMRIZORBMTD5HYL6B3Q37NCA62R6CECHAA5QQUY42PEZNJSRDGF3O42WEAEA6M3S2NRQOWKLEBBUA; __jdu=16883912243121671318379; SL_G_WPT_TO=zh-CN; SL_GWPT_Show_Hide_tmp=1; SL_wptGlobTipTmp=1; fp=504c197389599fc6bc841e9c6863357f; sensorsdata2015session=%7B%7D; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2210000090485%22%2C%22%24device_id%22%3A%2218967ebd86ac36-09c4152aa14d5d-1b525634-1d73c0-18967ebd86b24d3%22%2C%22props%22%3A%7B%7D%2C%22first_id%22%3A%2218967ebd86ac36-09c4152aa14d5d-1b525634-1d73c0-18967ebd86b24d3%22%7D; mba_muid=16883912243121671318379; __jd_ref_cls=elive_live_close_browser_pc; __jdv=101385626|direct|-|none|-|1690508534912; focus-team-id=00046419; focus-client=WEB; sso.jd.com=BJ.0491F8F3C641B3640F940E920BAD4EDB.8920230731091936; ssa.global.ticket=4BDA0D49851EED77CB8CE4197EE251DA; token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ik9OVjJCVmZpYjFkTU1Hd0FLcGdnIiwiaWF0IjoxNjkwNjAzMDkyLCJleHAiOjE2OTEyMDc4OTJ9.loMwLPGnud4VpJxzv9hp5XG_b5gvVs64S8y23UBNJLU; ssa.jd_cloud_disk_man=261e5b0a062e06d1905490d1a82fc9c13554bc08f22b983426df7ded66d58e615e008c9218867fa700e7d243a09668acf8cfac0136eae4093bd04f4a6ebdf7d887e9c66151725e5c2bc8e0393bde65f7f092dbe6eb601fcedfb0f0154bfb5db8d27515cd955d7da76a6d5c7058487c5b2fdb8f1de8d66d3316f48cfa7284ac2a; _pan_=A5AA8B6E99778C3A8DA6E0F4E7C88A36EBB0A7222A7E947BA856BF108D3B576A356F7030C91120F5F08178B6D58BC37A653851701F82768EFC36A2B5F533AEDA6B1CEF37F29002B661AC7B4FF3A1164C; focus-token=9657e1c616c92c86a0b7a5e363a5156e; __jda=137720036.16883912243121671318379.1688391224.1690766379.1690772418.120; __jdc=137720036; 3AB9D23F7A4B3C9B=TV5RVLRWZJHPDHK2OVZ3MIHGT4Q7EICTQWY4ZRKGAY7JWFRZZRTUTNO4YDAWX6FJYGP353KVAMZSZ6C4OO6QOSVWPY',
        'Origin': 'http://pan.jd.com',
        'Proxy-Connection': 'keep-alive',
        'Referer': 'http://pan.jd.com/home/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }

    data = {
        # 根据你的 cURL 命令中的请求表单数据填写
        # ...
        "paramsJson": '{"owner":"' + (owner or folder_uuid) + '","parentUuid":"' + folder_uuid + '","nameQueryKey":"","targetPage":' + str(page) + ',"perPageSize":20,"sortColumn":"updateTime","sortType":"DESC"}'
    }

    try:
        response = requests.post(url, headers=headers, data=data, verify=False)
        response.raise_for_status()
        json_data = response.json()
        if 'rows' in json_data['responseBody']:
            files = json_data['responseBody']['rows']
            for file in files:
                # 处理文件信息，这里可以输出文件的全路径和文件名
                # Check if the file has a suffix and if it is ".gz"
                if 'suffix' in file and file['suffix'] == '.tgz':
                    full_path = file['fullPathName']
                    file_name = file['name']
                    print(full_path, file_name)

                # 如果当前文件是文件夹，递归地获取该文件夹下的文件
                if file['type'] == 2:  # 2 表示文件夹
                    fetch_files(file['uuid'], file['owner'])

        # 如果还有更多的页数，继续递归获取下一页的文件
        if 'totalPageNumber' in json_data['responseBody']:
            total_pages = json_data['responseBody']['totalPageNumber']
            if page < total_pages:
                fetch_files(folder_uuid, owner, page + 1)

    except requests.exceptions.RequestException as e:
        print("发生异常：", e)

if __name__ == "__main__":
    folder_uuid = "068E5008092CFCB2F1B7EA1BA135FF87CEE6B9E79D93E578625D90D0B55BB2C6B2F0BE772629AF00"  # 将你要遍历的文件夹的uuid替换在此
    owner="FF93B3DD0BEF52F3F717319CFD494B7CDAE09D92B6BD5D610872C8164F98991D4AC4205E1F5EB2B5"
    fetch_files(folder_uuid, owner)