class ContextManager:
    def __init__(self):
        self.context={}
    def save_report(self,report):
        self.context=report
    def get_report(self):
        return self.context
    def clear(self):
        self.context={}
context_manager=ContextManager()