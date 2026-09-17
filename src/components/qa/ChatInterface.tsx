"use client";

import { useState, useRef, useEffect } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";
import http from "@/lib/http";
import { QAResponse } from "@/types";
import { toast } from "sonner";

interface Message {
  role: 'user' | 'assistant';
  content: string;
  refs?: { title: string; url: string }[];
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loadingResponse, setLoadingResponse] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const templates: string[] = [
    '如果青少年使用了含有拟除虫菊酯的驱蚊扣会引发什么症状？',
    '避蚊胺(DEET)的毒性数据是什么？',
    '拟除虫菊酯类化合物的毒理学研究进展如何？',
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (input.trim() === '') return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInput('');
    setLoadingResponse(true);

    try {
      const sessionId = getOrCreateSessionId();
      const response = await http.post<any, QAResponse>('/knowledge/qa', { question: input, sessionId }, { timeout: 120000 });
      const assistantMessage: Message = { role: 'assistant', content: response.answer, refs: response.refs };
      setMessages((prevMessages) => [...prevMessages, assistantMessage]);
    } catch (error) {
      toast.error("AI 问答服务出错，请稍后再试。");
      const errorMessage: Message = { role: 'assistant', content: "抱歉，我暂时无法回答您的问题。" };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setLoadingResponse(false);
    }
  };

  const getOrCreateSessionId = () => {
    try {
      const key = 'qa_session_id';
      let v = localStorage.getItem(key);
      if (!v) {
        v = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
        localStorage.setItem(key, v);
      }
      return v;
    } catch {
      return undefined;
    }
  };

  const handleSendTemplate = async (q: string) => {
    if (!q) return;
    const cleaned = q
      .replaceAll('“', '')
      .replaceAll('”', '')
      .replace(/^\s*(询问|请问|关于)\s*/g, '')
      .trim();
    setInput(cleaned);
    setTimeout(() => {
      if (!loadingResponse) {
        handleSendMessage();
      }
    }, 0);
  };

  const extractAlternatives = (content: string): string[] => {
    const idx = content.indexOf('你是否想找：');
    if (idx < 0) return [];
    const lineEnd = content.indexOf('\n', idx);
    const line = content.substring(idx, lineEnd > -1 ? lineEnd : content.length);
    const parts = line.split('：');
    if (parts.length < 2) return [];
    return parts[1].split('/').map(s => s.trim()).filter(Boolean);
  };

  const extractSuggestions = (content: string): string[] => {
    const anchor = '你可以试试：';
    const idx = content.indexOf(anchor);
    if (idx < 0) return [];
    const tail = content.substring(idx + anchor.length);
    const lines = tail.split('\n');
    const picks: string[] = [];
    for (const raw of lines) {
      const m = /^\s*-\s*(.+)$/.exec(raw.trim());
      if (m && m[1]) picks.push(m[1].trim());
    }
    return picks;
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-col gap-2 mb-2 flex-shrink-0">
        <p className="text-sm text-muted-foreground">基于科学文献的智能问答，试试点击以下问题：</p>
        <div className="flex flex-wrap gap-2">
          {templates.map((q) => (
            <Button key={q} size="sm" variant="secondary" onClick={() => handleSendTemplate(q)} disabled={loadingResponse}>
              {q}
            </Button>
          ))}
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-4 p-2 min-h-0">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-lg p-3 rounded-lg ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
              <p>{msg.content}</p>
              {msg.role === 'assistant' && (
                <>
                  {extractAlternatives(msg.content).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {extractAlternatives(msg.content).map((alt, ai) => (
                        <Button key={`${alt}-${ai}`} size="sm" variant="secondary" onClick={() => handleSendTemplate(`${alt}有哪些过敏原？`)}>
                          {alt}
                        </Button>
                      ))}
                    </div>
                  )}
                  {extractSuggestions(msg.content).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {extractSuggestions(msg.content).map((sug, si) => (
                        <Button key={`${sug}-${si}`} size="sm" variant="outline" onClick={() => handleSendTemplate(sug)}>
                          {sug}
                        </Button>
                      ))}
                    </div>
                  )}
                </>
              )}
              {msg.refs && msg.refs.length > 0 && (
                <div className="mt-2 text-xs text-muted-foreground">
                  <p className="font-semibold">参考资料:</p>
                  <ul className="list-disc pl-4">
                    {msg.refs.map((ref, refIndex) => (
                      <li key={refIndex}>
                        <a href={ref.url} target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">
                          {ref.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
        {loadingResponse && (
          <div className="flex justify-start">
            <div className="max-w-lg p-3 rounded-lg bg-muted animate-pulse">
              <p>AI 正在思考...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="mt-4 flex gap-2 flex-shrink-0">
        <Input
          placeholder="输入科学问题，基于文献库智能回答..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !loadingResponse) {
              handleSendMessage();
            }
          }}
          className="flex-1"
          disabled={loadingResponse}
        />
        <Button onClick={handleSendMessage} disabled={loadingResponse}>
          <Send className="h-4 w-4" />
          <span className="sr-only">发送</span>
        </Button>
      </div>
    </div>
  );
}
