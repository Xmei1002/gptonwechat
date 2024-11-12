from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf
from zhipuai import ZhipuAI
import json

class Session(object):

    def __init__(self, session_id, system_prompt=None):
        self.session_id = session_id
        file_content = self.get_file_content()
        system_prompt = "你是一个智能客服，旨在帮助用户解决相关问题。有人问你是谁的时候，请回答：我是智能客服，请问我能帮您做什么？" \
                        f"你职责是根据一下内容回答用户问题：\n{file_content}\n。如果用户问题与文档内容相关，请直接使用文档内容回答。" \
                        "如果用户问题与文档内容无关，请拒绝回答，并告诉用户：很抱歉，我无法回答这个问题。" \
                        "有些回答后面包含查看图片xx.png，如果有，则务必也回复 查看图片xx.png，不要省略。" \
                        "注意，你只能回答文档中有的内容，且所有回答尽可能简洁明了" \
                        "文档中不存在的内容，请勿回答。以免误导用户" \
                        "不要复述问题，直接回答即可"
        self.messages = []
        if system_prompt is None:
            self.system_prompt = conf().get("character_desc", "")
        else:
            self.system_prompt = system_prompt
    
    def get_file_content(self):
        '''根据已上传的文件id获取文件内容。例如：1731393349_7cef88cf78b3471192fb808350831ce1'''
        zhipu_ai_api_key = conf().get("zhipu_ai_api_key")
        client = ZhipuAI(api_key=zhipu_ai_api_key)
        file_content = json.loads(client.files.content(file_id='1731393349_7cef88cf78b3471192fb808350831ce1').content)["content"]
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
