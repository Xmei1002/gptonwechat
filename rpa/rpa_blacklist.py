from DrissionPage import ChromiumPage, ChromiumOptions
import os
import time  # 导入 time 模块

co = ChromiumOptions().auto_port()
# co.headless(True)  # 无头模式
co.set_argument("--window-size", "1000,700")
username = os.getenv("LINQU_USERNAME", 13777777777)
password = os.getenv("LINQU_PASSWORD", 7777777)
co.set_paths(browser_path="/usr/bin/google-chrome")  # 设置浏览器路径

def repJson(state, msg):
    return {"state": state, "msg": msg}

def addBlacklist(phone, url):
    try:
        if phone is None:
            return repJson('fail', "手机号不能为空")
        page = ChromiumPage(co)
        page.get(url)

        login_button = page.ele("@class=login-btn", timeout=2)
        if login_button:
            page.ele("@@class=el-input__inner@@type=text").input(username)
            page.ele("@@class=el-input__inner@@type=password").input(password)
            login_button.click()

        page.ele(".el-icon-s-cooperation").click()
        page.wait.ele_displayed("@class=el-menu--vertical", timeout=2)
        page.ele("text:运营管理").click()
        page.ele("text:收件人管理").click()
        page.ele("text:黑名单管理").click()
        page.ele("text:加入").click()
        print("进入黑名单管理")
        
    except Exception as e:
        print(e)
        return repJson('fail', "操作失败，等待人工处理")
    finally:
        page.quit()
        print("退出浏览器")

if __name__ == "__main__":
    print(addBlacklist("18737582236", "http://erp.linqugui.com/"))
