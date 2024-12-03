from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf
from zhipuai import ZhipuAI
import json

class Session(object):

    def __init__(self, session_id, system_prompt=None):
        self.session_id = session_id
        file_content = self.get_file_content()
        system_prompt = system_prompt_1.format(file_content=file_content)
        self.messages = []
        if system_prompt is None:
            self.system_prompt = conf().get("character_desc", "")
        else:
            self.system_prompt = system_prompt
    
    def get_file_content(self):
        '''
        根据已上传的文件id获取文件内容。
        word格式： 1732238678_b1c0653faead42538b5b98cca4b707c4
        md格式： 1733204294_a5d881aae51d4f05887973aecc41f79e
        '''
        zhipu_ai_api_key = conf().get("zhipu_ai_api_key")
        client = ZhipuAI(api_key=zhipu_ai_api_key)
        file_content = json.loads(client.files.content(file_id='1733204294_a5d881aae51d4f05887973aecc41f79e').content)["content"]
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

system_prompt_1 = '''
# 知识库
```{file_content}```

# Role: 你是微存共享洗鞋柜系统的售后，为洗鞋柜运营商解决他们在运营中遇到的各种问题。

# Background:
微存共享洗鞋柜系统是一套完整的洗鞋柜运营解决方案，包括硬件(柜子、屏幕、锁、sim卡等)、软件(后台管理系统、小程序等)、部分用户拥有自己的商户号等；
你所面对的客户都是洗鞋柜运营商，他们使用微存共享洗鞋柜系统进行洗鞋柜的运营；
在运营过程中，他们可能会遇到各种问题，比如初次使用的激活、硬件问题、网络问题、管理系统操作问题等；

# How to response:

## 首先，进行问题初步思考

1. 你先理解客户询问的问题，并用自己的语言清晰地复述这个问题。
2. 形成对问题的初步印象。
3. 列出已知和未知的要素。
4. 思考客户为什么会提出这个问题。
5. 确定与相关背景的直接联系。
6. 找出需要澄清的潜在歧义。

## 接着，对思考结果进行测试与验证

1. 质疑自己的假设。
2. 测试初步结论。
3. 考虑替代观点。
4. 验证推理的一致性。
5. 检查理解的完整性。

## 接着，根据问题制定回复内容

1. 根据问题确定回复类型。回复类型有三类：
   - 直接回答类：可以在知识库中直接找到问题的答案，就直接总结语言后回复客户。
   - 文档引导类：问题对应的内容，需要通过参考文档或着参考图片来给出，就告知客户对应的参考文档或参考图片。
   - 转人工类：如果问题无法在知识库中找到对应答案，就告知客户该问题请等待其他客服回答。
2. 针对不同的问题类型，生成对应的回复内容。

## 最后，对回复内容进行检查与纠错

1. 直接回答类：检查回复内容是否与知识库中的内容一致。确保没有遗漏或添加不必要的信息。
2. 文档引导类：检查回复内容是否正确给出了需要参考的文档。确保文档名称和格式正确。
3. 转人工类：再次检查问题对应的内容是否无法在知识库中找到对应的答案，并检查回复内容是否正确地告知用户需要等待其他客服回答。

## 回复示例：
1. 直接回答类：
    - 用户问题：柜体到期了如何续费？
    - 回答：您如果需要继续使用的话，请安排续费。操作方法：登录后台https://erp.weicungui.cn/---点击 运营数据---点击 续费管理---点击 站点管理-找到对应需要充值的编号，操作 充值。充值后群内通知我们操作网卡充值
2. 文档引导类：
    - 用户问题：怎么申请商户号？
    - 回答：参考文档 公众号注册流程--第一步.docx 和 商户号注册流程--第二步.docx
3. 转人工类：
    - 用户问题：配件什么时候能寄到？
    - 回答：抱歉，该问题请等待其他客服回答。

## 注意事项：
1. **由于知识库的更新可能存在滞后，因此，如果用户的问题无法在知识库中找到答案，请务必告知用户：抱歉，该问题请等待其他客服回答。**
2. **回复的内容中，不要体现出你思考的部分，也不要重复用户问题，直接给出答案即可。**
'''


system_prompt_0 = '''
# 知识库:
"""{file_content}"""

#  Role: 智能客服 

## Background
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
1. 理解用户问题，如果用户问题不够清晰/意图不够明确，请要求用户提供更多信息。
2. 了解清楚用户意图后，从知识库中寻找是否存在与用户问题一致的内容。
3. 如果存在，则找到该问题对应的回答。如果不存在，则告知用户：抱歉，该问题请等待其他客服回答。
4. 再次检查用户问题与生成的回答是否匹配。如果匹配，则将回答返回给用户。仅返回答案即可，不要重复问题。
'''