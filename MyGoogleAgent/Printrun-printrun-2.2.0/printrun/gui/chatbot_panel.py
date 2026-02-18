import wx
import threading
import uuid
import importlib
from google.adk.runners import InMemoryRunner
from google.genai import types
class ChatbotPanel(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        super(ChatbotPanel, self).__init__(parent, *args, **kwargs)

        self.parent_frame = parent 
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.chat_history = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        vbox.Add(self.chat_history, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        #self.chat_input = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.chat_input = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER, size=(-1, 60))
        self.send_button = wx.Button(self, label="Send")
        
        hbox.Add(self.chat_input, proportion=1, flag=wx.EXPAND | wx.RIGHT, border=5)
        hbox.Add(self.send_button, proportion=0, flag=wx.EXPAND)
        
        vbox.Add(hbox, proportion=0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=5)
        self.SetSizer(vbox)
        
        # self.send_button.Bind(wx.EVT_BUTTON, self.OnSend)
        # self.chat_input.Bind(wx.EVT_TEXT_ENTER, self.OnSend)
        
        self.send_button.Bind(wx.EVT_BUTTON, self.OnSend)
        self.chat_input.Bind(wx.EVT_KEY_DOWN, self.OnInputKeyDown)

        self.AppendChat("System", "Initializing Agent...")
        wx.CallLater(500, self.InitAgent)

    def OnInputKeyDown(self, event):
        """Handle Enter to send, Shift+Enter for new line."""
        if event.GetKeyCode() == wx.WXK_RETURN and not event.ShiftDown():
            # If Enter is pressed without Shift, prevent the newline and send!
            event.StopPropagation()
            self.OnSend(None)
        else:
            # Otherwise, let the text box behave normally (e.g., Shift+Enter adds a line)
            event.Skip()

    def InitAgent(self):
        try:
            agent_module = importlib.import_module('agent')
            self.agent = agent_module.root_agent
            self.wrapper = agent_module.printrun_client
            
            self.wrapper.init_parent(self.GetTopLevelParent())
            
            self.runner = InMemoryRunner(agent=self.agent, app_name="PronterfaceChatbot")
            self.session_id = str(uuid.uuid4())
            self.user_id = "local_user"
            
            # Removed create_session from here! It must happen in the background thread.
            
            self.AppendChat("System", f"Agent initialized! GUI hardware sharing active: {self.wrapper.is_gui_managed}")
        except Exception as e:
            self.AppendChat("System Error", f"Failed to initialize agent: {e}")

    def AppendChat(self, sender, text):
        self.chat_history.AppendText(f"{sender}: {text}\n\n")
        self.chat_history.ShowPosition(self.chat_history.GetLastPosition())

    def OnSend(self, event):
        user_text = self.chat_input.GetValue().strip()
        if not user_text:
            return
            
        self.chat_input.SetValue("")
        self.chat_input.Disable()
        self.send_button.Disable()
        
        self.AppendChat("You", user_text)
        threading.Thread(target=self.ProcessAgentResponse, args=(user_text,), daemon=True).start()

    def ProcessAgentResponse(self, user_text):
        """Launch an isolated asyncio event loop for this interaction."""
        import asyncio
        asyncio.run(self._async_agent_call(user_text))

    async def _async_agent_call(self, user_text):
        """Natively asynchronous ADK execution to prevent session memory loss."""
        try:
            # 1. Safely create the session inside this specific async loop
            if not hasattr(self, 'session_initialized'):
                await self.runner.session_service.create_session(
                    app_name="PronterfaceChatbot",
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                self.session_initialized = True
                
            # 2. Format the message
            from google.genai import types
            message_content = types.Content(
                role='user', 
                parts=[types.Part.from_text(text=user_text)]
            )
            
            # 3. Use run_async() to stay inside the same event loop
            async for event in self.runner.run_async(
                user_id=self.user_id, 
                session_id=self.session_id, 
                new_message=message_content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Safely check if the agent is using a tool
                        if getattr(part, 'function_call', None):
                            tool_msg = f"🔧 [Agent is using tool: {part.function_call.name}]"
                            wx.CallAfter(self.AppendChat, "System", tool_msg)
                        
                        # Safely capture any text the agent speaks
                        elif getattr(part, 'text', None):
                            if part.text.strip():
                                wx.CallAfter(self.AppendChat, "Agent", part.text.strip())
            
        except Exception as e:
            wx.CallAfter(self.AppendChat, "System Error", f"Agent execution failed: {e}")
        finally:
            wx.CallAfter(self.chat_input.Enable)
            wx.CallAfter(self.send_button.Enable)
            wx.CallAfter(self.chat_input.SetFocus)
