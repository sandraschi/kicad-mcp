import { useCallback, useEffect, useRef, useState } from 'react';
import { apiGet, apiPost } from '../lib/api';
import { Download, Eraser, Send } from 'lucide-react';

const STORAGE_KEY = 'kicad-mcp-chat-history';
const PERSONALITY_KEY = 'kicad-mcp-chat-personality';

const PERSONALITIES: Record<string, string> = {
  'PCB Designer': "You are a senior PCB design engineer. Be precise, practical, and reference specific KiCad tools. Suggest complete workflows.",
  'Component Specialist': "You are a component engineer. Focus on part selection, footprint compatibility, and supply chain. Reference datasheets when possible.",
  'DFM Reviewer': "You are a design-for-manufacturing expert. Inspect designs for fabrication issues, suggest layout improvements, and flag DRC violations.",
  'Custom': '',
};

const EXAMPLE_PROMPTS = [
  { group: 'Design', prompts: ['Run DRC on my board and summarize issues', 'Place a 0.1uF decoupling cap near the IC', 'Export Gerbers for JLCPCB fabrication'] },
  { group: 'Inspect', prompts: ['Show me the component list on this board', 'Check ERC on the schematic', 'What nets are connected on F.Cu?'] },
  { group: 'Export', prompts: ['Generate BOM in CSV format', 'Export the board as a 3D STEP file', 'Create fabrication PDF with dimensions'] },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<{ role: string; content: string; ts?: string }[]>(() => {
    try { const saved = localStorage.getItem(STORAGE_KEY); return saved ? JSON.parse(saved).slice(-100) : []; } catch { return []; }
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [personalityId, setPersonalityId] = useState(() => localStorage.getItem(PERSONALITY_KEY) || 'PCB Designer');
  const [customPrompt, setCustomPrompt] = useState('');
  const [skillContent, setSkillContent] = useState('');
  const [skillName, setSkillName] = useState('');
  const [providerStatus, setProviderStatus] = useState('detecting...');
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    apiGet('/api/v1/skills').then((d) => {
      if (d.skills?.length > 0) {
        const primary = d.skills[0].name;
        setSkillName(d.skills[0].title);
        apiGet(`/api/v1/skills/${primary}`).then((s) => setSkillContent(s.content || ''));
      }
    }).catch(() => {});
    apiGet('/api/v1/llm/discover').then((d) => {
      const detected = d.providers?.filter((p: any) => p.status === 'detected');
      setProviderStatus(detected?.length > 0 ? detected.map((p: any) => `${p.name} :${p.port}`).join(', ') : 'not detected');
    }).catch(() => setProviderStatus('not detected'));
  }, []);

  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-100))); }, [messages]);
  useEffect(() => { localStorage.setItem(PERSONALITY_KEY, personalityId); }, [personalityId]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const buildSystemPrompt = useCallback(() => {
    const personality = personalityId === 'Custom' ? customPrompt : PERSONALITIES[personalityId] || '';
    return `${skillContent}\n\n---\n\n## Role\n${personality}`;
  }, [personalityId, customPrompt, skillContent]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    const userMsg = { role: 'user', content: text, ts: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    const system = buildSystemPrompt();
    const history = [...messages, userMsg].map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.content }));
    try {
      const r = await apiPost('/api/v1/llm/chat', { model: 'llama3.2:latest', system, messages: history, stream: false });
      const reply = r.choices?.[0]?.message?.content || 'No response from LLM.';
      setMessages((prev) => [...prev, { role: 'assistant', content: reply, ts: new Date().toISOString() }]);
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Error: Could not reach the LLM backend. Ensure Ollama or LM Studio is running.', ts: new Date().toISOString() }]);
    }
    setLoading(false);
  }, [input, loading, messages, buildSystemPrompt]);

  const handleExport = () => {
    const text = messages.map((m) => `[${m.ts?.slice(0, 19) || ''}] ${m.role === 'user' ? 'You' : 'Assistant'}: ${m.content}`).join('\n\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `kicad-mcp-chat-${Date.now()}.txt`; a.click();
    URL.revokeObjectURL(url);
  };

  const handleClear = () => { setMessages([]); localStorage.removeItem(STORAGE_KEY); };

  return (
    <div data-testid="chat-page" className="flex flex-col h-full">
      {/* Controls bar */}
      <div data-testid="chat-controls" className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 bg-gray-900/50 shrink-0">
        <select
          data-testid="personality-select"
          value={personalityId}
          onChange={(e) => setPersonalityId(e.target.value)}
          className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1 text-xs"
        >
          {Object.keys(PERSONALITIES).map((p) => <option key={p}>{p}</option>)}
        </select>
        {skillName && <span className="text-xs text-gray-500">skill:{skillName}</span>}
        {personalityId === 'Custom' && (
          <input className="flex-1 bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1 text-xs" placeholder="Custom system prompt..." value={customPrompt} onChange={(e) => setCustomPrompt(e.target.value)} />
        )}
        <div className="flex items-center gap-1 ml-auto">
          <span className={`w-1.5 h-1.5 rounded-full ${providerStatus === 'not detected' ? 'bg-red-500' : 'bg-green-500'}`} />
          <span className="text-xs text-gray-500">LLM: {providerStatus}</span>
        </div>
        <button data-testid="chat-export" onClick={handleExport} disabled={messages.length === 0} className="p-1.5 rounded text-gray-400 hover:text-white disabled:opacity-30" title="Export chat"><Download className="w-3.5 h-3.5" /></button>
        <button data-testid="chat-clear" onClick={handleClear} disabled={messages.length === 0} className="p-1.5 rounded text-gray-400 hover:text-white disabled:opacity-30" title="Clear"><Eraser className="w-3.5 h-3.5" /></button>
      </div>

      {/* Messages */}
      <div data-testid="chat-messages" className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">Ask me anything about PCB design with KiCad.</p>
            <div data-testid="example-prompts" className="space-y-3">
              {EXAMPLE_PROMPTS.map((g) => (
                <div key={g.group}>
                  <p className="text-xs text-gray-600 mb-1">{g.group}</p>
                  <div className="flex flex-wrap gap-2">
                    {g.prompts.map((p) => (
                      <button key={p} onClick={() => { setInput(p); inputRef.current?.focus(); }} className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded-full transition-colors">{p}</button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${m.role === 'user' ? 'bg-emerald-900/60 text-emerald-200' : 'bg-gray-800 text-gray-200'}`}>
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.ts && <p className="text-xs text-gray-500 mt-1">{m.ts.slice(11, 19)}</p>}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-lg px-4 py-2 text-sm text-gray-400">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 p-3 shrink-0">
        <div className="flex gap-2">
          <textarea
            data-testid="chat-input"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Ask about PCB design..."
            rows={1}
            className="flex-1 bg-zinc-800 text-zinc-100 border border-zinc-600 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-emerald-500"
          />
          <button data-testid="chat-send" onClick={handleSend} disabled={!input.trim() || loading} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 text-white rounded-lg px-3 py-2 transition-colors">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
