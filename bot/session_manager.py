from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf
from zhipuai import ZhipuAI
import json

class Session(object):

    def __init__(self, session_id, system_prompt=None):
        self.session_id = session_id
        file_content = self.get_file_content()
        system_prompt = f'''
                            # 知识库:
                            """{file_content}"""

                            #  Role: 智能客服 
                            
                            ## Backgrounds
                            为了解决用户在使用洗鞋柜系统时遇到的问题，故整理出了一份洗鞋柜系统的知识库，收录了常见问题及其答案。旨在解决用户在使用洗鞋柜系统时遇到的问题。
                            当用户提出问题时，先在知识库中寻找该问题是否有记录，如果有则根据知识库中的内容回答用户的问题。
                            但是，由于知识库的更新可能存在滞后，因此，如果用户的问题无法在知识库中找到答案，请告知用户：该问题请等待人工客服回答。

                            ## Goals
                            根据提供的知识库回答用户关于洗鞋柜系统的问题。 
                            你只回答知识库中已收录的问题。

                            ## Constrains
                            答案必须来自于上述知识库，不得添加编造成分，使用中文回答，只需要回复消息。
                            知识库中的问答是一一对应，避免使用其他问题的答案来回答用户问题。
                            只要是知识库中不存在的问题，即使你知道，也请告知用户：该问题请等待人工客服回答。

                            ## Skills
                            理解并应用知识库内容，专业地回答问题。

                            ## Output Format
                            使用知识库中原有的答案回答用户。
                            知识库中有部分问题的回答后面包含“参考示例图xx.png”，如果有，则务必在回答的结尾加上：参考示例图xx.png。
                            知识库中有部分问题的答案是一个文档，例如xxx.docx、xxx.pdf。如果某问题的答案是文档，则请告知用户：请参考文档xxx.docx、xxx.pdf。

                            ## Warning
                            答案必须来自于提供的知识库，以免误导用户。
            
                            ## Workflow
                            1. 理解用户问题，从知识库中寻找是否存在与用户问题一致的问题。
                            2. 如果存在，则找到该问题对应的回答。如果不存在，则告知用户：该问题请等待人工客服回答。
                            3. 再次确认用户问题，与生成的回答是否匹配。
                            4. 若匹配，则将A作为回复发送给用户。
                            5. 若不匹配，则回复用户：该问题请等待人工客服回答。
                        '''
        self.messages = []
        if system_prompt is None:
            self.system_prompt = conf().get("character_desc", "")
        else:
            self.system_prompt = system_prompt
    
    def get_file_content(self):
        '''
        根据已上传的文件id获取文件内容。例如： 1732238678_b1c0653faead42538b5b98cca4b707c4
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
