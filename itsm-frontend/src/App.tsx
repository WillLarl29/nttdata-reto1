import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import {
  Send,
  Bot,
  User,
  LayoutDashboard,
  Ticket,
  Settings,
  BookOpen,
  LogOut,
  Bell,
  Search,
  Menu,
} from "lucide-react";
import "./App.css";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  timestamp: Date;
  ticketId?: string;
  ticketUrl?: string;
  status?: string;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "msg-init",
      sender: "bot",
      text: "Hola, soy GENIA, tu Asistente Inteligente de IT. ¿En qué puedo ayudarte hoy? Puedes reportar un incidente o hacer una consulta.",
      timestamp: new Date(),
    },
  ]);

  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Generate a random session ID on load
  const [sessionId] = useState(
    () => `sess_${Math.random().toString(36).substring(2, 9)}`,
  );
  const userEmail = "soporte@nttdata.com"; // Simulated logged in user

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const newUserMsg: Message = {
      id: `msg-${Date.now()}`,
      sender: "user",
      text: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setInputValue("");
    setIsLoading(true);

    try {
      // Connect to the real backend running locally on port 8000
      const response = await axios.post("http://localhost:8000/api/v1/chat", {
        session_id: sessionId,
        user_email: userEmail,
        message: newUserMsg.text,
      });

      const { reply, status, ticket_id, ticket_url } = response.data;

      const newBotMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        sender: "bot",
        text:
          reply || "He procesado tu solicitud, pero no hubo respuesta clara.",
        status: status,
        ticketId: ticket_id,
        ticketUrl: ticket_url,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, newBotMsg]);
    } catch (error) {
      console.error("Error communicating with backend:", error);
      const errorMsg: Message = {
        id: `msg-err-${Date.now()}`,
        sender: "bot",
        text: "Lo siento, ha ocurrido un error al intentar conectarme con los servicios de soporte.",
        status: "error",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <Menu size={24} className="text-primary" />
          <span className="sidebar-logo">NTT DATA ITSM</span>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-item">
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </div>
          <div className="nav-item active">
            <Bot size={20} />
            <span>Asistente GenIA</span>
          </div>
          <div className="nav-item">
            <Ticket size={20} />
            <span>Mis Tickets</span>
          </div>
          <div className="nav-item">
            <BookOpen size={20} />
            <span>Base de Conocimiento</span>
          </div>
          <div style={{ flex: 1 }}></div>
          <div className="nav-item">
            <Settings size={20} />
            <span>Configuración</span>
          </div>
          <div className="nav-item" style={{ color: "var(--color-danger)" }}>
            <LogOut size={20} />
            <span>Cerrar Sesión</span>
          </div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Topbar */}
        <header className="topbar glass-panel">
          <div className="topbar-title">
            Asistente Inteligente de Soporte TI
          </div>

          <div className="topbar-actions">
            <button className="btn-icon">
              <Search size={20} />
            </button>
            <button className="btn-icon" style={{ position: "relative" }}>
              <Bell size={20} />
              <span
                style={{
                  position: "absolute",
                  top: 4,
                  right: 4,
                  width: 8,
                  height: 8,
                  backgroundColor: "var(--color-danger)",
                  borderRadius: "50%",
                }}
              ></span>
            </button>

            <div className="user-profile">
              <div
                className="avatar bg-primary"
                style={{
                  backgroundColor: "var(--color-primary)",
                  color: "white",
                }}
              >
                W
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                  Willman
                </span>
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--color-text-muted)",
                  }}
                >
                  IT Support L1
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Workspace Content */}
        <div className="content-area">
          <div className="chat-container">
            <div className="chat-messages animate-fade-in">
              {messages.map((msg) => (
                <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
                  <div className="message-meta">
                    {msg.sender === "bot" ? (
                      <Bot size={14} />
                    ) : (
                      <User size={14} />
                    )}
                    {msg.sender === "bot" ? "GenIA Assistant" : "Tú"}
                    <span style={{ marginLeft: "auto", opacity: 0.7 }}>
                      {msg.timestamp.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>

                  <div
                    className={`message-bubble ${msg.sender === "user" ? "bg-primary" : ""}`}
                  >
                    {msg.text}

                    {msg.ticketId && (
                      <div className="ticket-card animate-fade-in">
                        <div className="ticket-header">
                          <strong>Ticket Creado Exitosamente</strong>
                          <span className="ticket-badge badge-incident">
                            {msg.ticketId}
                          </span>
                        </div>
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                          }}
                        >
                          <span>
                            <strong>Estado Asistente:</strong> {msg.status}
                          </span>
                          {msg.ticketUrl && (
                            <a
                              href={msg.ticketUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                color: "var(--color-secondary)",
                                textDecoration: "none",
                                display: "flex",
                                alignItems: "center",
                                gap: "4px",
                                marginTop: "6px",
                              }}
                            >
                              Ver ticket en Jira <Ticket size={14} />
                            </a>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="message-wrapper bot">
                  <div className="message-meta">
                    <Bot size={14} /> GenIA Assistant
                  </div>
                  <div className="typing-indicator">
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-area glass-panel">
              <div className="chat-input-wrapper">
                <input
                  type="text"
                  className="chat-input"
                  placeholder="Describe tu incidente o solicitud..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                />
                <button
                  className="send-btn"
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isLoading}
                >
                  <Send size={18} />
                </button>
              </div>
              <div
                style={{
                  textAlign: "center",
                  fontSize: "0.75rem",
                  color: "var(--color-text-muted)",
                  marginTop: "8px",
                }}
              >
                GenIA Assistant puede cometer errores. Verifica la información
                antes de actuar.
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
