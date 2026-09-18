"""从行动记录正文里抽取人名（规则法；装了 jieba 时用其词典过滤常见词、并补充其识别的人名）。

处理的写法：
    姓名 + 称谓        王艳萍老师、李经理、张工、屈文杰老师
    称谓 + 姓名        纯化组长屈文杰、采购史德均、总经理姚林
    姓名 + 姓 + 称谓   付玉清付总
    姓 + 称谓          彭老师、李总（只有姓氏，另行标记）

抽取难免有漏有错，结果供人工核对。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

SURNAMES_TEXT = (
    "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付傅方白邹孟熊秦"
    "邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤常温康施文牛樊葛邢安齐易乔伍庞颜倪庄聂章鲁岳翟殷詹申欧耿关兰焦俞左柳甘祝包宁尚符舒阮柯纪梅童"
    "凌毕单季裴霍涂成苗谷盛曲翁冉骆蓝路游辛靳管柴蒙鲍华喻祁蒲房滕屈饶解牟艾尤阳时穆农司卓古吉缪简车项连芦麦褚娄窦戚岑景党宫费卜冷晏席卫米柏宗瞿桂全佟应"
    "臧闵伊仲宣邬云贲屠戈嵇祖敖狄栾廉羊惠甄麻贡邰谈索来阙湛蔺贝盖裘边扈燕冀郏浦别习茹宦鱼容慎庾终暨居衡步都满弘匡国寇广禄殳沃利蔚越夔隆师巩厍晁勾融訾阚那"
    "空毋沙乜养鞠须丰巢蒯相查后荆红竺权逯益桓公晋楚法汝鄢钦归海帅缑亢况郈琴商佘佴伯赏墨哈谯笪年爱仉督寿通苟侬闻莘劳逄姬扶堵宰郦雍郤璩桑濮"
)
COMPOUND_SURNAMES = ["欧阳", "司马", "诸葛", "上官", "皇甫", "尉迟", "公孙", "慕容", "长孙", "宇文", "司徒", "端木", "东方", "南宫", "独孤", "夏侯", "轩辕", "令狐",
                     "呼延", "澹台", "淳于", "太史", "申屠", "公羊", "百里", "东郭", "闻人", "赫连", "拓跋", "万俟", "钟离", "鲜于", "闾丘", "司空", "仲孙", "公冶", "宗政", "濮阳"]
# 这些字虽是罕见姓氏，但更常作虚词 / 常用词出现（都、那、后…），不当作姓
_NOT_SURNAME = set("都那后来有相别空满广东国海商年爱通越利法公权益红查关沙养须丰融冷容慎终居衡步弘匡禄沃蔚隆师巩勾毋巢荆竺桓晋楚汝钦归帅亢况琴伯赏墨哈督寿苟闻劳扶堵宰雍桑索谈贡麻甄惠羊廉祖屠宣仲伊应")
SURNAMES: Set[str] = set(SURNAMES_TEXT) - _NOT_SURNAME

# 姓名后面的称谓（长的在前，避免“总”吞掉“总经理”）
TITLES_AFTER = ["总经理", "总监", "总工", "总助", "董事长", "工程师", "负责人", "研究员", "技术员", "老师", "经理", "主任", "组长", "博士", "教授", "女士", "先生",
                "小姐", "部长", "院长", "所长", "主管", "老板", "药师", "医生", "大夫", "科长", "处长", "课长", "站长", "校长", "书记", "局长", "厂长", "同学",
                "师兄", "师姐", "师傅", "助理", "秘书", "会计", "阿姨", "总", "工", "董", "博", "哥", "姐"]
# 机构 / 地点用字：出现在候选名字的名部分时，多半是“××组”“××部”被切进来了（陈兴农组陈老师 → 排除“农组陈”）
ORG_CHARS = set("组部室处科院所司厂校系课队班站局会社委办馆园区省市县镇村街路号楼层栋座厅店铺行网台")
# 姓名前面的称谓 / 角色
TITLES_BEFORE = ["总经理", "副总经理", "董事长", "总监", "负责人", "研究员", "技术员", "工程师", "采购员", "实验员", "组长", "经理", "采购", "主任", "老师", "同事", "同学",
                 "博士", "教授", "主管", "老板", "部长", "院长", "所长", "科长", "药师", "销售", "助理", "秘书", "财务", "会计", "库管", "仓管", "领导", "专员",
                 "研发", "技术", "生产", "质量", "品保", "品控", "纯化", "合成", "分析", "客户", "联系人", "朋友", "校友", "学生", "研究生", "博士生", "硕士", "QC", "QA"]
# 手工补充的常见词（第二个字或首字是姓，但整体不是人名）；装了 jieba 时再并入其词典
HAND_WORDS = set("对方 我方 贵方 双方 各方 甲方 乙方 官方 厂方 校方 院方 公司 上司 施工 加工 手工 分工 返工 停工 化工 竣工 完工 高工 总工 员工 女工 男工 技工 民工 木工 精工 "
                 "轻工 重工 开工 做工 老总 副总 汇总 上海 北京 南京 天津 西安 山东 山西 河南 河北 湖南 湖北 广东 广西 江苏 江西 浙江 福建 云南 贵州 四川 陕西 甘肃 "
                 "青海 海南 辽宁 吉林 安徽 宁夏 新疆 西藏 华为 华南 华北 华东 华中 中山 中南 大连 长春 长沙 常州 苏州 杭州 广州 深圳 成都 重庆 武汉 郑州 合肥 济南 "
                 "青岛 厦门 福州 昆明 贵阳 南宁 海口 南昌 太原 兰州 银川 西宁 沈阳 月旭 大曹 岛津 安捷 沃特 赛默 依利 汉邦 纳微 博格 蓝晓 西陇 麦克 阿拉 国药 药明 "
                 "合全 凯莱 京东 淘宝 天猫 顺丰 德邦 圆通 中通 申通 韵达 极兔 方案 方法 方向 方面 方式 方便 路线 路上 路过 成本 成品 成分 成果 成立 成功 成交 金额 "
                 "金属 白天 白色 高温 高压 高效 高端 高层 高校 高级 高度 高速 常规 常见 常用 石油 石墨 叶片 云端 安装 安排 安全 文件 文档 文章 牛奶 马上 龙头 农药 "
                 "时间 时候 车间 车辆 连续 连接 项目 游离 季度 单位 单独 单价 单子 单据 程序 程度 尚未 许多 许可 阳性 毛细 华人 康复 田间 于是 卫生 温度 严格 严重 "
                 "万元 万一 章节 甘油 包装 包括 包裹 舒服 梅雨 曲线 管理 管道 柴油 房间 屈服 解决 解释 尤其 阳光 时刻 司机 卓越 古代 吉利 简单 简介 简称 车站 景区 "
                 "党员 费用 冷却 冷藏 席位 米色 柏树 宗旨 桂林 全部 全国 全新 全面 全程 应用 应该 应对 应收 应急 伊利 宣传 宣布 祖国 廉价 羊毛 贡献 谈判 谈话 索性 "
                 "索取 来源 来自 来回 贝壳 盖子 边缘 边上 别人 别的 庄园 充分 充电 终于 终端 居然 衡量 步骤 都是 满意 满足 国内 国外 国家 国际 国产 广泛 广告 东西 "
                 "利用 利润 利益 师傅 师姐 师兄 师弟 关系 关于 关注 关键 相关 相信 相比 相对 查看 查询 后续 后面 后来 红色 红外 权限 权利 益生 公司 法国 法律 法规 "
                 "海外 海关 有限 有效 有关 有些 有点 有时 有人 商务 商品 商业 商量 年度 年底 年初 年前 年后 通过 通知 通常 通用 空气 空间 曾经 养殖 丰富 后天 "
                 "研发 技术 生产 销售 市场 财务 行政 人事 仓库 部门 中心 学院 大学 医院 药业 生物 科技 集团 工厂 总部 办公 课题 团队 实验 纯化 合成 分析 质量 "
                 "品保 品控 采购 客户 老板 领导 同事 拜访 联系 电话 微信 沟通 见到 找到 认识 介绍 推荐 跟进 询问 了解 表示 反馈 之前 上次 这次 今天 昨天 明天 "
                 "最近 目前 现在 那边 这边 他们 我们 你们 咱们 一位 两位 几位 新来 新的 原来 以前 以及 报价 询价 下单 订单 合同 发货 到货 收货 付款 回款 开票 "
                 "发票 样品 试用 试样 填料 色谱 液相 制备 检测 工艺 设备 仪器 柱子 中试 放大 小试 批次 数量 价格 折扣 优惠 活动 促销 展会 会议 培训 交流 参观 "
                 "考察 出差 路上 顺便 一起 共同 单独 "
                 # 药品 / 项目常用缩写与词（司美格鲁肽、替尔泊肽、氯苯那敏…）
                 "司美 替尔 利拉 度拉 艾塞 卡格 索马 奥曲 亮丙 戈舍 曲普 布舍 特立 阿托 缩宫 胸腺 胰岛 谷胱 环孢 达托 卡泊 米卡 万古 替考 多粘 恩夫 阿巴 比伐 齐考 "
                 "西曲 加尼 地加 那敏 伊可 司莫 替曲 普兰 醋酸 头孢 青霉 阿莫 克拉 罗红 阿奇 左氧 莫西 氟康 伏立 卡泊 米卡 他汀 沙坦 普利 地平 洛尔 格列 列净 "
                 "肽昇 甘宝 "
                 # 色谱行业品牌 / 同行（不是人名）
                 "安谱 盛瀚 月旭 纳微 博格 蓝晓 赛分 汉邦 依利 博蕴 喆分 辰桥 微纯 科斯 科思 大曹 岛津 安捷 沃特 赛默 菲罗 谱析 迪马 中谱 纳谱 谱柱 色谱 "
                 "大赛 赛璐 赛露 苏州 兰博 蓝博 盛迪 尚瑞 安礼 元延 九阳 华世 药明 康德 博腾 凯莱 合全 药石 诺泰 翰宇 圣诺 海慈 扬子 恒瑞 齐鲁 石药 "
                 "华海 华东 华北 华胜 正大 天晴 信达 奥翔 皓元 百川 泓沛 健元 祥根 探真 齐谱 鼎元 宇健 诺澳 珍典 多禧 迈乐 巨亨 铭迹 慧聚 山目 阿法 "
                 "紫杉 申基 德药 京卫 双元 泰和 全宇 先强 孔圣 红日 康仁 威高 富康 托普 新时 新时代 佰成 中海 伊诺 达博 汇宇 吉晟 科莱 信达 泰康 橙达 乾泰 国为 "
                 "闪亮 浔奉 北方 环境 双鹭 寿康 方林 中智 曲靖 迪因 神奇 楚昊 衡楚 东方 达灵 健安 天然 检验 检测 认证 计量 质检 药检 疾控 "
                 "康龙 药明 桑迪 博恩 千里 立康 药宜 鑫立 康亚 盛翔 盛祥 全和 键凯 紫杉 迎成 和仁 昊邦 瑞邦 赛立 天马 天吉 鲁银 奇力 诚创 蓝海 葛蓝 新通 "
                 "蓝博 蓝博思 博思 恒瑞 正元 盛邦 绿霸 科伦 益佰 千里眼 博恩特 迪因 茂宏 赛升 百草 泰克 兴普 信立 信立泰 诚创 孔府 云鹏 凯源 齐鲁 "
                 "艾杰尔 露娜 康百达 驭成 九信 湃肽 和泽 普瑞 西岭 肽库 康希 沃华 天铭 赛普 济煜 晶海 博鳌 昆药 日中天 纳通 前沿 全和诚 键凯 同达 盛林 "
                 "唐山 甘精 蓝纳 蓝纳成 东宝 华康 九洲 九州 辰欣 迪赛 华谱 奥萨 麻叶 红日 东诚 华震".split())
# 名字后面若紧跟这些二字词，说明名字到此为止（“金舫询问”→ 金舫）
FOLLOW_BIGRAMS = set("询问 沟通 了解 表示 介绍 反馈 推荐 说到 提到 提出 认为 觉得 希望 计划 打算 准备 需要 想要 要求 询价 报价 下单 购买 采购 试用 使用 反映 回复 答复 "
                     "电话 微信 那边 这边 他们 这个 那个 目前 现在 最近 已经 还是 也是 就是 都是 不是 没有 正在 可以 可能 应该 表达 告诉 问了 说了 给了 发了 寄了 "
                     "带了 来了 去了 到了 见了 约了 做了 用了 买了 换了 试了 看了 听了 打了 老师 先生 女士 经理 主任 负责 组长 采购 研发 技术 博士 教授 同学 今天 "
                     "昨天 明天 上午 下午 晚上 中午 早上 刚刚 刚好 正好 一直 一起 一同 本人 本身 自己 亲自 当面 当时 当天 后续 后面 前面 前期 后期 近期 近日 "
                     "不在 在家 出差 休假 请假 忙于 正忙 很忙 太忙 有事 没空 在外 外出 开会 上课 上班 下班 加班 值班 出国 回国 离职 退休 调岗 升职 接手 "
                     "对接 联系 拜访 见面 会面 约见 约谈 面谈 面见 交流 讨论 商量 商议 洽谈 咨询 请教 求助 帮忙 帮助 协助 配合 支持 认可 同意 答应 拒绝 "
                     "推脱 推辞 婉拒 谢绝 接受 收下 收到 拿到 得到 获得 取得 拿走 带走 送来 寄来 发来 交给 转给 递给 转交 移交 交接 回馈 回访 回电 回信 "
                     "进行 处理 安排 确认 完成 开展 参与 参加 加入 主导 组织 跟踪 提供 发送 带来 拿来 接到 看到 听到 想到 谈到 聊到 讲到 问到 找到 见到 遇到 碰到 "
                     "回答 回应 表态 表明 强调 指出 感觉 期望 请求 建议 分享 转发 转达 传达 通知 告知 通报 汇报 反应 那里 这里 那儿 这儿 等人 等等 及其 以及 "
                     "组的 组里 课题 团队 手里 手上 这块 那块 这个 那个 老板 处长 科长 一直 直接 马上 立即 稍后 随后 然后 之后 以后 以前 之前 当时 刚才".split())
# 几乎不会出现在人名里的虚词 / 动词字
STOP_CHARS = set("的了是我你您咱他她它们被把将呢吗啊吧么什这那哪就都很也和与跟给对而且但因所以并或则即每各该此之及等不没已还又请让说问到去回聊谈陪姓")
_CJK = "一-鿿"

_vocab: Set[str] = set(HAND_WORDS)
_dict_nr: Set[str] = set()   # jieba 词典里标为人名的词（其中不少并非人名：蒲公英、连云港、盖章…），不采信
_vocab_loaded = False
_context_orgs: List[str] = []  # 当前记录所属客户名称等：其片段不当作人名（药宜立康詹老师 → 詹老师）


def load_vocab() -> int:
    """装了 jieba 时把其词典里的常见二、三字词并入（人名词性除外），用于排除“方案”“公司”这类假人名。"""
    global _vocab_loaded
    if _vocab_loaded:
        return len(_vocab)
    _vocab_loaded = True
    try:
        import jieba  # type: ignore
        from pathlib import Path
        path = Path(jieba.__file__).resolve().parent / "dict.txt"
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) != 3:
                continue
            word, freq, pos = parts
            if pos.startswith("nr"):
                _dict_nr.add(word)
            elif 2 <= len(word) <= 3 and int(freq) >= 20:
                _vocab.add(word)
    except Exception:  # noqa: BLE001
        pass
    return len(_vocab)


def is_word(s: str) -> bool:
    return s in _vocab


@dataclass
class Mention:
    name: str          # 抽出的姓名（或“姓 + 称谓”）
    start: int
    end: int
    surname_only: bool  # 只有姓氏（如“彭老师”）
    source: str         # registered / rule / jieba

    @property
    def surname(self) -> str:
        for cs in COMPOUND_SURNAMES:
            if self.name.startswith(cs):
                return cs
        return self.name[:1]


def _is_surname_start(text: str) -> Tuple[bool, int]:
    for cs in COMPOUND_SURNAMES:
        if text.startswith(cs):
            return True, 2
    return (text[:1] in SURNAMES), 1


def _plausible_name(cand: str) -> bool:
    ok, sn_len = _is_surname_start(cand)
    if not ok or len(cand) <= sn_len or len(cand) > 3:
        return False
    if not re.fullmatch(f"[{_CJK}]+", cand):
        return False
    if any(ch in STOP_CHARS for ch in cand[sn_len:]):
        return False
    if any(cand[sn_len:] == t or cand[sn_len:].endswith(t) for t in TITLES_AFTER):
        return False  # “钟工”“李总”是姓 + 称谓，不是全名
    if any(ch in ORG_CHARS for ch in cand[sn_len:]):
        return False
    if is_word(cand) or is_word(cand[:2]):
        return False
    if len(cand) == 3 and is_word(cand[1:3]) and cand[1:3] in HAND_WORDS:
        return False
    return True


def _straddles_word(text: str, pos: int) -> bool:
    """位置 pos 处的切分是否切开了一个常见词或客户名称片段（“连云港童老师”里在“云”前切开会切断“连云港”）。"""
    for a, b in ((pos - 1, pos + 1), (pos - 1, pos + 2), (pos - 2, pos + 1)):
        if a >= 0 and b <= len(text):
            seg = text[a:b]
            if re.fullmatch(f"[{_CJK}]+", seg) and (is_word(seg) or any(seg in org for org in _context_orgs)):
                return True
    return False


def _pick_name_before_title(text: str, title_pos: int, title: str = "") -> Optional[Tuple[int, int, bool]]:
    """称谓前的姓名：向前取至多 3 个汉字。返回 (start, end, surname_only)。"""
    for length in (3, 2):
        cand_start = title_pos - length
        if cand_start < 0:
            continue
        cand = text[cand_start:title_pos]
        if not _plausible_name(cand):
            continue
        if _straddles_word(text, cand_start):
            continue  # 前面的字与首字组成常见词（公司李总 → 排除“司李”；连云港童老师 → 排除“云港童”）
        return cand_start, title_pos, False
    cand_start = title_pos - 1
    ch = text[cand_start:title_pos] if cand_start >= 0 else ""
    if ch in SURNAMES:
        if _straddles_word(text, cand_start) or (title and is_word(ch + title)):
            return None  # 对方老师 / 公司李总 里的“方”“司”；施工 / 高工 / 老总
        return cand_start, title_pos, True
    return None


def _boundary_after(text: str, pos: int) -> bool:
    """pos 处是否可作为名字的结尾：后面是标点 / 空白 / 结尾 / 常见接续词 / 称谓 / 虚词。"""
    nxt = text[pos:pos + 2]
    if not nxt or not re.match(f"[{_CJK}]", nxt[0]):
        return True
    if nxt[0] in STOP_CHARS or nxt in FOLLOW_BIGRAMS or (len(nxt) == 2 and is_word(nxt)):
        return True  # 名字后面紧跟一个常见词（张晨阳进行了…）
    return any(text.startswith(t, pos) for t in TITLES_AFTER)


def _pick_name_after_title(text: str, pos: int) -> Optional[Tuple[int, int]]:
    """称谓后的姓名：组长屈文杰，/ 采购史德均老师。"""
    for length in (3, 2):
        cand = text[pos:pos + length]
        if len(cand) < length or not _plausible_name(cand):
            continue
        if not _boundary_after(text, pos + length) or _straddles_word(text, pos + length):
            continue
        return pos, pos + length
    return None


def extract_names(text: str, known: Iterable[str] = (), exclude: Iterable[str] = (), use_jieba: bool = False,
                  orgs: Iterable[str] = ()) -> List[Mention]:
    """抽取正文里的人名。known：该客户已建档联系人姓名（优先精确匹配）；exclude：本公司人员等不计入的名字；
    orgs：客户名称等机构名，其片段不当作人名。"""
    load_vocab()
    global _context_orgs
    _context_orgs = [o for o in orgs if o and len(o) >= 3]
    mentions: List[Mention] = []
    taken = [False] * (len(text) + 1)

    def occupy(a: int, b: int) -> bool:
        if any(taken[a:b]):
            return False
        for i in range(a, b):
            taken[i] = True
        return True

    exclude_set = {e for e in exclude if e}
    # 1) 已建档联系人姓名精确匹配（长名优先）
    for name in sorted({k for k in known if k and len(k) >= 2}, key=len, reverse=True):
        for m in re.finditer(re.escape(name), text):
            if occupy(m.start(), m.end()):
                mentions.append(Mention(name, m.start(), m.end(), False, "registered"))
    # 2) 本公司人员名字：占位不输出
    for name in sorted({e for e in exclude_set if len(e) >= 2}, key=len, reverse=True):
        for m in re.finditer(re.escape(name), text):
            occupy(m.start(), m.end())
    # 3) 姓名 + 姓 + 称谓：付玉清付总
    title_after_re = "|".join(re.escape(t) for t in TITLES_AFTER)
    for m in re.finditer(f"([{_CJK}])([{_CJK}]{{1,2}})\\1({title_after_re})", text):
        cand = m.group(1) + m.group(2)
        if _plausible_name(cand) and not _straddles_word(text, m.start()) and occupy(m.start(), m.end()):
            mentions.append(Mention(cand, m.start(), m.start() + len(cand), False, "rule"))
    # 4) 姓名 + 称谓
    for m in re.finditer(f"({title_after_re})", text):
        title, pos = m.group(1), m.start()
        after = text[m.end():m.end() + 1]
        if title in ("工", "董", "博", "哥", "姐") and after and re.match(f"[{_CJK}]", after) and (is_word(title + after) or after in "作艺程厂业资事们妹姐哥士览物客弈"):
            continue  # 工艺 / 工作 / 董事 / 博士 / 哥们 …
        if title == "博" and not _boundary_after(text, m.end()):
            continue  # “蓝博思”里的“博”
        if title == "总" and after in ("是", "共", "结", "计", "部", "体", "额", "量", "价", "数", "之", "的", "会", "算", "得", "能", "要", "在", "有", "觉"):
            continue
        picked = _pick_name_before_title(text, pos, title)
        if not picked:
            continue
        a, b, surname_only = picked
        if any(taken[a:m.end()]):
            continue
        occupy(a, m.end())
        label = text[a:m.end()] if surname_only else text[a:b]
        mentions.append(Mention(label, a, b, surname_only, "rule"))
    # 5) 称谓 + 姓名
    title_before_re = "|".join(re.escape(t) for t in sorted(TITLES_BEFORE, key=len, reverse=True))
    for m in re.finditer(f"({title_before_re})的?", text):
        picked = _pick_name_after_title(text, m.end())
        if not picked:
            continue
        a, b = picked
        if any(taken[a:b]):
            continue
        occupy(a, b)
        mentions.append(Mention(text[a:b], a, b, False, "rule"))
    # 6) jieba 识别的人名（可选补充）：只采信词典里没有、由其模型判断出来的人名，且要求有上下文佐证
    if use_jieba:
        for word, a, b in jieba_names(text):
            if any(taken[a:b]) or word in exclude_set or word in _dict_nr or is_word(word):
                continue
            title = next((t for t in TITLES_AFTER if word.endswith(t) and len(word) > len(t)), None)
            if title and word[:-len(title)] in SURNAMES and len(word) - len(title) == 1:
                occupy(a, b)
                mentions.append(Mention(word, a, b - len(title), True, "jieba"))  # 马工 → 仅姓氏
                continue
            if not _plausible_name(word) or not _boundary_after(text, b) or _straddles_word(text, b):
                continue
            if len(word) == 2:
                before = text[max(0, a - 4):a]
                ok_before = any(before.endswith(t) for t in TITLES_BEFORE) or before.endswith("娘") or before.endswith("人")
                nxt = text[b:b + 2]
                ok_after = (not nxt or not re.match(f"[{_CJK}]", nxt[0]) or nxt in FOLLOW_BIGRAMS or any(text.startswith(t, b) for t in TITLES_AFTER))
                if not (ok_before or ok_after):
                    continue
            occupy(a, b)
            mentions.append(Mention(word, a, b, False, "jieba"))
    mentions = [x for x in mentions if x.name not in exclude_set]
    # 同一段文字里“金老师”与“金舫”视为同一人：去掉能对上全名的仅姓氏提法
    full_surnames = {x.surname for x in mentions if not x.surname_only}
    mentions = [x for x in mentions if not (x.surname_only and x.surname in full_surnames)]
    # 同名去重
    seen: Dict[str, Mention] = {}
    for x in sorted(mentions, key=lambda x: x.start):
        seen.setdefault(x.name, x)
    return list(seen.values())


def jieba_names(text: str) -> List[Tuple[str, int, int]]:
    """装了 jieba 时，返回其词性标注为人名的片段。未安装返回空列表。"""
    try:
        import jieba.posseg as pseg  # type: ignore
    except Exception:  # noqa: BLE001
        return []
    out = []
    pos = 0
    for word, flag in pseg.cut(text):
        start = text.find(word, pos)
        if start < 0:
            continue
        pos = start + len(word)
        if flag in ("nr", "nrfg", "nrt") and 2 <= len(word) <= 3:
            out.append((word, start, start + len(word)))
    return out
