# -*- coding: UTF-8 -*-
"""
__Author__ = "BlueCestbon"
__Version__ = "2.1.0"
__Description__ = "大麦app抢票自动化 - 优化版（支持场次选择）"
__Created__ = 2025/09/13 19:27
"""

import time
from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import Config


class DamaiBot:
    def __init__(self):
        self.config = Config.load_config()
        self.driver = None
        self.wait = None
        self._setup_driver()

    def _setup_driver(self):
        """初始化驱动配置"""
        capabilities = {
            "platformName": "Android",  # 操作系统
            "platformVersion": "13",  # 系统版本
            "deviceName": "emulator-5554",  # 设备名称
            "appPackage": "cn.damai",  # app 包名
            "appActivity": ".launcher.splash.SplashMainActivity",  # app 启动 Activity
            "unicodeKeyboard": True,  # 支持 Unicode 输入
            "resetKeyboard": True,  # 隐藏键盘
            "noReset": True,  # 不重置 app
            "newCommandTimeout": 6000,  # 超时时间
            "automationName": "UiAutomator2",  # 使用 uiautomator2
            "skipServerInstallation": False,  # 跳过服务器安装
            "ignoreHiddenApiPolicyError": True,  # 忽略隐藏 API 策略错误
            "disableWindowAnimation": True,  # 禁用窗口动画
            # 优化性能配置
            "mjpegServerFramerate": 1,  # 降低截图帧率
            "shouldTerminateApp": False,
            "adbExecTimeout": 20000,
        }

        device_app_info = AppiumOptions()
        device_app_info.load_capabilities(capabilities)
        self.driver = webdriver.Remote(self.config.server_url, options=device_app_info)

        # 更激进的性能优化设置
        self.driver.update_settings({
            "waitForIdleTimeout": 0,  # 空闲时间，0 表示不等待，让 UIAutomator2 不等页面"空闲"再返回
            "actionAcknowledgmentTimeout": 0,  # 禁止等待动作确认
            "keyInjectionDelay": 0,  # 禁止输入延迟
            "waitForSelectorTimeout": 300,  # 从500减少到300ms
            "ignoreUnimportantViews": False,  # 保持false避免元素丢失
            "allowInvisibleElements": True,
            "enableNotificationListener": False,  # 禁用通知监听
        })

        # 极短的显式等待，抢票场景下速度优先
        self.wait = WebDriverWait(self.driver, 2)  # 从5秒减少到2秒

    def ultra_fast_click(self, by, value, timeout=1.5):
        """超快速点击 - 适合抢票场景"""
        try:
            # 直接查找并点击，不等待可点击状态
            el = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            # 使用坐标点击更快
            rect = el.rect
            x = rect['x'] + rect['width'] // 2
            y = rect['y'] + rect['height'] // 2
            self.driver.execute_script("mobile: clickGesture", {
                "x": x,
                "y": y,
                "duration": 50  # 极短点击时间
            })
            return True
        except TimeoutException:
            return False

    def batch_click(self, elements_info, delay=0.1):
        """批量点击操作"""
        for by, value in elements_info:
            if self.ultra_fast_click(by, value):
                if delay > 0:
                    time.sleep(delay)
            else:
                print(f"点击失败: {value}")

    def ultra_batch_click(self, elements_info, timeout=2):
        """超快批量点击 - 带等待机制"""
        coordinates = []
        # 批量收集坐标，带超时等待
        for by, value in elements_info:
            try:
                # 等待元素出现
                el = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                rect = el.rect
                x = rect['x'] + rect['width'] // 2
                y = rect['y'] + rect['height'] // 2
                coordinates.append((x, y, value))
            except TimeoutException:
                print(f"超时未找到用户: {value}")
            except Exception as e:
                print(f"查找用户失败 {value}: {e}")
        print(f"成功找到 {len(coordinates)} 个用户")
        # 快速连续点击
        for i, (x, y, value) in enumerate(coordinates):
            self.driver.execute_script("mobile: clickGesture", {
                "x": x,
                "y": y,
                "duration": 30
            })
            if i < len(coordinates) - 1:
                time.sleep(0.01)
            print(f"点击用户: {value}")

    def smart_wait_and_click(self, by, value, backup_selectors=None, timeout=1.5):
        """智能等待和点击 - 支持备用选择器"""
        selectors = [(by, value)]
        if backup_selectors:
            selectors.extend(backup_selectors)

        for selector_by, selector_value in selectors:
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((selector_by, selector_value))
                )
                rect = el.rect
                x = rect['x'] + rect['width'] // 2
                y = rect['y'] + rect['height'] // 2
                self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y, "duration": 50})
                return True
            except TimeoutException:
                continue
        return False

    # 已知的阻挡型弹窗按钮（可以安全关闭）
    KNOWN_DISMISS_BUTTONS = [
        # 大麦主题弹窗（票务公告等）
        (By.ID, "cn.damai:id/damai_theme_dialog_confirm_btn"),
        # 通用弹窗按钮文本
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("知道了")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("确认并知悉")'),
        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("我知道了")'),
    ]

    # 已知的流程型弹窗标记（包含这些元素的不关闭）
    KNOWN_FLOW_ELEMENTS = [
        "cn.damai:id/layout_viewers",      # 选择观众
        "cn.damai:id/recycler_viewers",     # 观众列表
        "cn.damai:id/tv_select_viewers",    # 选择观众标题
    ]

    def _dismiss_dialogs(self):
        """关闭已知的阻挡型弹窗，流程型弹窗不关闭
        debug模式下遇到未知弹窗暂停等待用户处理"""
        dismissed = True
        while dismissed:
            dismissed = False

            # 先检查是否是流程型弹窗（选择观众等），如果是则跳过
            for flow_id in self.KNOWN_FLOW_ELEMENTS:
                try:
                    self.driver.find_element(By.ID, flow_id)
                    return  # 是流程型弹窗，不处理
                except NoSuchElementException:
                    continue

            for selector in self.KNOWN_DISMISS_BUTTONS:
                try:
                    el = WebDriverWait(self.driver, 0.5).until(
                        EC.presence_of_element_located(selector)
                    )
                    # 用坐标点击，避免StaleElement
                    rect = el.rect
                    x = rect['x'] + rect['width'] // 2
                    y = rect['y'] + rect['height'] // 2
                    self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y, "duration": 50})
                    print("已关闭弹窗")
                    time.sleep(0.3)
                    dismissed = True
                    break  # 重新从第一个selector开始检查
                except (TimeoutException, Exception):
                    continue

            # debug模式：检查是否有未知弹窗（有弹窗遮罩层 + 未知按钮）
            if not dismissed and self.config.debug:
                try:
                    # 只有存在弹窗遮罩层时才认为有弹窗
                    has_dialog = False
                    dialog_indicators = [
                        "cn.damai:id/damai_theme_dialog_layout",  # 大麦主题弹窗
                        "android:id/alertTitle",                    # 系统弹窗标题
                    ]
                    for indicator in dialog_indicators:
                        try:
                            self.driver.find_element(By.ID, indicator)
                            has_dialog = True
                            break
                        except NoSuchElementException:
                            continue

                    if has_dialog:
                        print("\n⚠️  DEBUG: 检测到未知弹窗")
                        print("请手动处理弹窗，处理完后按回车继续...")
                        input()
                        dismissed = True
                except Exception:
                    pass

    def _select_session(self):
        """选择场次 - 根据配置的日期选择对应场次"""
        try:
            # 方式1: 通过日期文本直接点击
            date_text = self.config.date  # e.g. "07.26"
            # 尝试多种日期格式匹配
            date_selectors = [
                (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{date_text}")'),
                (By.XPATH, f'//*[contains(@text,"{date_text}")]'),
            ]
            # 也尝试 "07月26" 格式
            if '.' in date_text:
                month_day = date_text.replace('.', '月') + '日'
                date_selectors.append(
                    (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{month_day}")')
                )
                # 也尝试 "7月26" 格式（去掉前导零）
                parts = date_text.split('.')
                month = str(int(parts[0]))
                day = str(int(parts[1]))
                date_selectors.append(
                    (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{month}月{day}")')
                )

            for selector in date_selectors:
                try:
                    el = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located(selector)
                    )
                    rect = el.rect
                    x = rect['x'] + rect['width'] // 2
                    y = rect['y'] + rect['height'] // 2
                    self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y, "duration": 50})
                    print(f"通过日期文本选择场次成功: {date_text}")
                    time.sleep(0.3)
                    return True
                except TimeoutException:
                    continue

            # 方式2: 通过场次容器，优先选择有票的场次
            print("日期文本未找到，尝试通过场次容器选择...")
            try:
                session_container = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, 'cn.damai:id/project_detail_perform_flowlayout'))
                )
                # 获取所有场次item
                session_items = session_container.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().className("android.view.ViewGroup").clickable(true)'
                )
                print(f"找到 {len(session_items)} 个场次")

                # 优先选择没有"无票"标签的场次
                for idx, item in enumerate(session_items):
                    try:
                        tag = item.find_element(AppiumBy.ANDROID_UIAUTOMATOR,
                                                'new UiSelector().resourceId("cn.damai:id/tv_tag")')
                        tag_text = tag.text
                        if tag_text and '无票' not in tag_text and '缺货' not in tag_text:
                            rect = item.rect
                            x = rect['x'] + rect['width'] // 2
                            y = rect['y'] + rect['height'] // 2
                            self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y, "duration": 50})
                            print(f"选择有票场次成功 (index={idx}, 标签: {tag_text})")
                            time.sleep(0.3)
                            return True
                    except NoSuchElementException:
                        # 没有标签 = 可能有票
                        rect = item.rect
                        x = rect['x'] + rect['width'] // 2
                        y = rect['y'] + rect['height'] // 2
                        self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y, "duration": 50})
                        print(f"选择无标签场次 (index={idx}，可能有票)")
                        time.sleep(0.3)
                        return True

                # 所有场次都有"无票"标签，按配置的date推算index点击
                if '.' in self.config.date:
                    parts = self.config.date.split('.')
                    month = int(parts[0])
                    day = int(parts[1])
                    # 根据已知场次顺序推算: 07.24=index0, 07.25=index1, 07.26=index2, ...
                    # 计算与第一场(07.24)的天数差
                    first_day = 24  # 第一场是7月24号
                    session_index = day - first_day
                    if session_index >= 0 and session_index < len(session_items):
                        item = session_items[session_index]
                        rect = item.rect
                        x = rect['x'] + rect['width'] // 2
                        y = rect['y'] + rect['height'] // 2
                        self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y, "duration": 50})
                        print(f"按推算index={session_index}选择场次")
                        time.sleep(0.3)
                        return True

                print("所有场次均无票且无法匹配")
                return False

            except TimeoutException:
                print("未找到场次容器")
                return False

        except Exception as e:
            print(f"场次选择异常: {e}")
            return False

    def _select_price(self):
        """选择票价 - 在选完场次后选择票价档位"""
        try:
            # 等待票价容器出现（选完场次后才会出现）
            price_container = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.ID, 'cn.damai:id/project_detail_perform_price_flowlayout'))
            )
            # 在容器内找对应index且clickable的FrameLayout
            target_price = price_container.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().className("android.widget.FrameLayout").index({self.config.price_index}).clickable(true)'
            )
            self.driver.execute_script('mobile: clickGesture', {'elementId': target_price.id})
            print(f"票价选择成功 (price_index={self.config.price_index})")
            time.sleep(0.3)
            return True
        except TimeoutException:
            print("票价容器未出现，可能页面未加载完成")
            return False
        except NoSuchElementException:
            print(f"未找到 price_index={self.config.price_index} 的票价档位")
            # 备用: 尝试通过价格文本点击
            try:
                price_text = self.config.price  # e.g. "1517"
                price_el = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().textContains("{price_text}")'
                )
                rect = price_el.rect
                x = rect['x'] + rect['width'] // 2
                y = rect['y'] + rect['height'] // 2
                self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y, "duration": 50})
                print(f"通过价格文本选择成功: {price_text}")
                time.sleep(0.3)
                return True
            except Exception:
                print("价格文本匹配也失败")
                return False
        except Exception as e:
            print(f"票价选择异常: {e}")
            return False

    def _select_quantity(self):
        """选择购票数量"""
        if self.driver.find_elements(by=By.ID, value='layout_num'):
            clicks_needed = len(self.config.users) - 1
            if clicks_needed > 0:
                try:
                    plus_button = self.driver.find_element(By.ID, 'img_jia')
                    for i in range(clicks_needed):
                        rect = plus_button.rect
                        x = rect['x'] + rect['width'] // 2
                        y = rect['y'] + rect['height'] // 2
                        self.driver.execute_script("mobile: clickGesture", {
                            "x": x,
                            "y": y,
                            "duration": 50
                        })
                        time.sleep(0.02)
                    print(f"数量选择成功: {len(self.config.users)}张")
                except Exception as e:
                    print(f"快速点击加号失败: {e}")

    def _go_back_to_detail_page(self):
        """尝试返回演出详情页，用于重试前恢复页面状态"""
        for _ in range(5):  # 最多按5次返回
            try:
                # 如果已经在详情页（能找到预约按钮），就不需要再返回
                self.driver.find_element(By.ID, "cn.damai:id/trade_project_detail_purchase_status_bar_container_fl")
                print("已回到演出详情页")
                return True
            except NoSuchElementException:
                pass
            # 按返回键
            self.driver.press_keycode(4)  # KEYCODE_BACK
            time.sleep(0.5)
            # 顺便关闭可能弹出的弹窗
            self._dismiss_dialogs()
        print("未能回到演出详情页")
        return False

    def run_ticket_grabbing(self):
        """执行抢票主流程 - 每个步骤失败时返回详情页重试，每步前后都清理弹窗"""
        max_step_retries = 3  # 每个步骤最多重试次数

        for step_attempt in range(max_step_retries):
            try:
                if step_attempt > 0:
                    print(f"\n--- 步骤重试第 {step_attempt} 次 ---")
                    # 返回详情页重新开始
                    self._go_back_to_detail_page()
                    self._dismiss_dialogs()

                print("开始抢票流程...")
                start_time = time.time()

                # 1. 城市选择
                self._dismiss_dialogs()
                print("选择城市...")
                city_selectors = [
                    (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{self.config.city}")'),
                    (AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().textContains("{self.config.city}")'),
                    (By.XPATH, f'//*[@text="{self.config.city}"]')
                ]
                if not self.smart_wait_and_click(*city_selectors[0], city_selectors[1:]):
                    print("城市选择失败，返回重试")
                    continue
                self._dismiss_dialogs()

                # 2. 点击预约按钮
                self._dismiss_dialogs()
                print("点击预约按钮...")
                book_selectors = [
                    (By.ID, "cn.damai:id/trade_project_detail_purchase_status_bar_container_fl"),
                    (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*预约.*|.*购买.*|.*立即.*")'),
                    (By.XPATH, '//*[contains(@text,"预约") or contains(@text,"购买")]')
                ]
                if not self.smart_wait_and_click(*book_selectors[0], book_selectors[1:]):
                    # 可能被弹窗挡住了，尝试关闭弹窗再点一次
                    self._dismiss_dialogs()
                    if not self.smart_wait_and_click(*book_selectors[0], book_selectors[1:], timeout=2):
                        print("预约按钮点击失败，返回重试")
                        continue
                self._dismiss_dialogs()

                # 3. 选择场次
                self._dismiss_dialogs()
                print("选择场次...")
                if not self._select_session():
                    print("场次选择失败，返回重试")
                    continue
                self._dismiss_dialogs()

                # 4. 票价选择
                self._dismiss_dialogs()
                print("选择票价...")
                if not self._select_price():
                    print("票价选择失败，返回重试")
                    continue
                self._dismiss_dialogs()

                # 5. 数量选择
                self._dismiss_dialogs()
                print("选择数量...")
                self._select_quantity()
                self._dismiss_dialogs()

                # 6. 确定购买
                self._dismiss_dialogs()
                print("确定购买...")
                if not self.ultra_fast_click(By.ID, "cn.damai:id/btn_buy_view"):
                    # 备用按钮文本
                    self.ultra_fast_click(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*确定.*|.*购买.*")')
                self._dismiss_dialogs()

                # 7. 批量选择用户
                self._dismiss_dialogs()
                print("选择用户...")
                user_clicks = [(AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{user}")') for user in
                               self.config.users]
                self.ultra_batch_click(user_clicks)
                self._dismiss_dialogs()

                # 8. 提交订单
                self._dismiss_dialogs()
                if self.config.if_commit_order:
                    print("提交订单...")
                    submit_selectors = [
                        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().text("立即提交")'),
                        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textMatches(".*提交.*|.*确认.*")'),
                        (By.XPATH, '//*[contains(@text,"提交")]')
                    ]
                    self.smart_wait_and_click(*submit_selectors[0], submit_selectors[1:])
                else:
                    print("if_commit_order=false，跳过提交订单，请手动确认")

                end_time = time.time()
                print(f"抢票流程完成，耗时: {end_time - start_time:.2f}秒")
                return True

            except Exception as e:
                print(f"抢票过程发生错误: {e}")
                continue

        print(f"步骤重试 {max_step_retries} 次均失败")
        return False

    def run_with_retry(self, max_retries=3):
        """带重试机制的抢票 - 外层重试会重新初始化驱动"""
        for attempt in range(max_retries):
            print(f"\n===== 第 {attempt + 1} 次尝试 =====")
            if self.run_ticket_grabbing():
                print("抢票成功！")
                return True
            else:
                print(f"第 {attempt + 1} 次尝试失败")
                if attempt < max_retries - 1:
                    print("3秒后重试（重新初始化驱动）...")
                    time.sleep(3)
                    # 重新初始化驱动
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self._setup_driver()

        print("所有尝试均失败")
        return False


# 使用示例
if __name__ == "__main__":
    bot = DamaiBot()
    bot.run_with_retry(max_retries=3)
