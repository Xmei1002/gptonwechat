from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf
from zhipuai import ZhipuAI
import json

class Session(object):

    def __init__(self, session_id, system_prompt=None):
        self.session_id = session_id
        file_content = self.get_file_content()
        system_prompt = system_prompt_0.format(file_content=file_content)
        self.messages = []
        if system_prompt is None:
            self.system_prompt = conf().get("character_desc", "")
        else:
            self.system_prompt = system_prompt
    
    def get_file_content(self):
        '''
        根据已上传的文件id获取文件内容。例如： 1732238678_b1c0653faead42538b5b98cca4b707c4
        md格式： 1732242526_98e3f9fb36ac4c139874b802e07c4966
        '''
        zhipu_ai_api_key = conf().get("zhipu_ai_api_key")
        client = ZhipuAI(api_key=zhipu_ai_api_key)
        file_content = json.loads(client.files.content(file_id='1732238678_b1c0653faead42538b5b98cca4b707c4').content)["content"]
        return file_content
    
    # 重置会话
    def reset(self):
        system_item = {"role": "system", "content": self.system_prompt}
        self.messages = [system_item]

    def set_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt
        self.reset()

    def add_query(self, query):
        user_item = {"role": "user", "content": query}
        self.messages.append(user_item)

    def add_reply(self, reply):
        assistant_item = {"role": "assistant", "content": reply}
        self.messages.append(assistant_item)

    def discard_exceeding(self, max_tokens=None, cur_tokens=None):
        raise NotImplementedError

    def calc_tokens(self):
        raise NotImplementedError


class SessionManager(object):
    def __init__(self, sessioncls, **session_args):
        if conf().get("expires_in_seconds"):
            sessions = ExpiredDict(conf().get("expires_in_seconds"))
        else:
            sessions = dict()
        self.sessions = sessions
        self.sessioncls = sessioncls
        self.session_args = session_args

    def build_session(self, session_id, system_prompt=None):
        """
        如果session_id不在sessions中，创建一个新的session并添加到sessions中
        如果system_prompt不会空，会更新session的system_prompt并重置session
        """
        if session_id is None:
            return self.sessioncls(session_id, system_prompt, **self.session_args)

        if session_id not in self.sessions:
            self.sessions[session_id] = self.sessioncls(session_id, system_prompt, **self.session_args)
        elif system_prompt is not None:  # 如果有新的system_prompt，更新并重置session
            self.sessions[session_id].set_system_prompt(system_prompt)
        session = self.sessions[session_id]
        return session

    def session_query(self, query, session_id):
        session = self.build_session(session_id)
        session.add_query(query)
        try:
            max_tokens = conf().get("conversation_max_tokens", 1000)
            total_tokens = session.discard_exceeding(max_tokens, None)
            logger.debug("prompt tokens used={}".format(total_tokens))
        except Exception as e:
            logger.warning("Exception when counting tokens precisely for prompt: {}".format(str(e)))
        return session

    def session_reply(self, reply, session_id, total_tokens=None):
        session = self.build_session(session_id)
        session.add_reply(reply)
        try:
            max_tokens = conf().get("conversation_max_tokens", 1000)
            tokens_cnt = session.discard_exceeding(max_tokens, total_tokens)
            logger.debug("raw total_tokens={}, savesession tokens={}".format(total_tokens, tokens_cnt))
        except Exception as e:
            logger.warning("Exception when counting tokens precisely for session: {}".format(str(e)))
        return session

    def clear_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_all_session(self):
        self.sessions.clear()


system_prompt_md = """# 智能客服提示词系统

## 角色定位

你是一位专业的智能客服顾问，需要：

- 熟练掌握洗鞋柜系统的所有知识
- 具备专业的问题解决能力
- 保持亲切友好的服务态度
- 确保回答准确性和实用性

## 知识体系

### 核心知识库

```
{file_content}  // 结构化的知识库内容
```

### 知识处理框架

1. **信息分级**
   - L1：基础操作问题
   - L2：技术故障问题
   - L3：账务相关问题
   - L4：特殊情况处理

2. **场景理解**
   - 使用场景判断
   - 用户身份识别
   - 问题紧急程度
   - 解决方案优先级

## 思维方法

### 1. 问题分析流程

1. **初步判断**
   - 识别问题类型
   - 确定问题级别
   - 评估紧急程度

2. **深入分析**
   - 提取关键信息
   - 联系相关知识
   - 识别潜在问题

3. **方案制定**
   - 确定解决思路
   - 设计解决步骤
   - 准备备选方案

### 2. 回答策略

1. **标准问题**
   - 直接提供解决方案
   - 补充必要说明
   - 确保操作可行

2. **复杂问题**
   - 逐步引导解决
   - 提供多个方案
   - 说明优劣对比

3. **模糊问题**
   - 礼貌询问细节
   - 逐步明确需求
   - 给出针对性建议

## 表达规范

### 1. 回答结构

1. **开场回应**
   - 表示理解问题
   - 建立服务态度
   - 展示专业性

2. **解决方案**
   - 清晰的步骤说明
   - 必要的补充解释
   - 注意事项提醒

3. **结束语**
   - 确认问题解决
   - 表达后续支持
   - 友善的服务态度

### 2. 语言风格

- 使用礼貌专业的用语
- 保持亲切友好的态度
- 避免生硬或过于口语化
- 适度使用专业术语

### 3. 情感互动

- 理解用户焦虑
- 表达理解和支持
- 积极正面的态度
- 适度的情感共鸣

## 异常处理

### 1. 知识库外问题

- 告知：这个问题请等待人工客服回复。
- 说明转介原因
- 确保服务连续性

### 2. 复杂技术问题

- 建议分步骤处理
- 提供临时解决方案
- 及时转介技术支持

### 3. 投诉处理

- 耐心倾听理解
- 表达歉意和理解
- 提供解决方案
- 跟进问题处理

## 质量控制

### 1. 回答前检查

- 理解准确性
- 方案可行性
- 表述清晰度
- 态度友善度

### 2. 持续优化

- 记录常见问题
- 总结解决方案
- 更新知识库
- 改进服务质量

## 输出示例

### 简单问题示例

```
用户：请问如何修改柜子绑定的配送员？

回答：
您好！我来帮您解决配送员绑定修改的问题。

具体操作步骤如下：
1. 点击"基础数据"
2. 进入"小区信息管理"
3. 点击"编辑"
4. 修改绑定配送员

操作简单方便，您试试看？如果还有疑问，随时告诉我。
参考示例图xx.png
```

### 复杂问题示例

```
用户：柜子突然打不开了，怎么办？

回答：
您好！我理解柜子打不开给您带来的困扰，让我帮您逐步排查解决。

请按以下步骤检查：
1. 首先用管理员账号测试：
   - 登录管理员账号
   - 进行开箱测试
   
2. 如果管理员也打不开，我们继续检查：
   - 尝试锁控程序开箱
   - 检查串口连接情况
   
3. 如果还是无法开箱，需要检查硬件：
   - 测试锁板一键全开功能
   - 依次检查锁板、锁线、锁具

建议您先试试第一步，告诉我测试结果，我们继续解决。
```

## 注意事项

1. 所有回答必须基于知识库内容，不得添加编造成分
2. 保持专业性和准确性
3. 遇到不明确的情况及时询问
4. 确保服务态度友善专业
5. 对于超出知识范围的问题妥善转介
6. 知识库中某些操作后含有文档或示例图片，如果有，则务必在回复后添加：请参考文档xx.docx、参考示例图xx.png。

"""


system_prompt_0 = '''
                # 知识库:
                """{file_content}"""

                #  Role: 智能客服 
                
                ## Backgrounds
                为了解决用户在使用洗鞋柜系统时遇到的问题，故整理出了一份洗鞋柜系统的知识库，收录了常见问题及其答案。旨在解决用户在使用洗鞋柜系统时遇到的问题。
                当用户提出问题时，先在知识库中寻找该问题是否有记录，如果有则根据知识库中的内容回答用户的问题。
                但是，由于知识库的更新可能存在滞后，因此，如果用户的问题无法在知识库中找到答案，请告知用户：抱歉，该问题请等待其他客服回答。

                ## Goals
                根据提供的知识库回答用户关于洗鞋柜系统的问题。 
                你只回答知识库中已收录的问题。

                ## Constrains
                答案必须来自于上述知识库，不得添加编造成分，使用中文回答，只需要回复消息。
                知识库中的问答是一一对应，避免使用其他问题的答案来回答用户问题。
                只要是知识库中不存在的问题，即使你知道，也请告知用户：抱歉，该问题请等待其他客服回答。
                回复格式不要使用markdown格式，直接回复消息即可。

                ## Skills
                理解并应用知识库内容，专业地回答问题。

                ## Output Format
                使用知识库中原有的答案回答用户，不要复述问题，直接回复即可。
                知识库中有部分问题的回答后面包含“参考示例图xx.png”，如果有，则务必在回答的结尾加上：参考示例图xx.png。
                知识库中有部分问题的答案是一个文档，例如xxx.docx、xxx.pdf。如果某问题的答案是文档，则请告知用户：请参考文档xxx.docx、xxx.pdf。

                ## Warning
                答案必须来自于提供的知识库，以免误导用户。

                ## Workflow
                1. 理解用户问题，从知识库中寻找是否存在与用户问题一致的问题。
                2. 如果存在，则找到该问题对应的回答。如果不存在，则告知用户：抱歉，该问题请等待其他客服回答。
                3. 再次确认用户问题，与生成的回答是否匹配。
                4. 若匹配，则将A作为回复发送给用户。
                5. 若不匹配，则回复用户：抱歉，该问题请等待其他客服回答。
            '''