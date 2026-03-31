"use client";

import { useState, useRef } from "react";
import TopBar from "../../components/TopBar";
import MessageList from "../../components/MessageList";
import InputBar from "../../components/InputBar";
import ActionSheet from "../../components/ActionSheet";
import ImagePreview from "../../components/ImagePreview";
import { sendMessageStream } from "../../lib/api";
import { useAuth } from "../../lib/useAuth";
import { useTranslation } from "../../lib/i18n";

export default function ChatPage() {
  const { user, loading } = useAuth();
  const { t } = useTranslation();

  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [agentType, setAgentType] = useState("companion");
  const [isLoading, setIsLoading] = useState(false);
  const [pendingImage, setPendingImage] = useState(null);
  const [pendingImageFile, setPendingImageFile] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const msgIdRef = useRef(0);

  if (loading || !user) return null;

  const nextId = () => {
    msgIdRef.current += 1;
    return msgIdRef.current;
  };

  const handleSend = ({ text, audio, image, imagePreview }) => {
    const userMsgId = nextId();
    const userMsg = {
      id: userMsgId,
      role: "user",
      content: text || (audio ? `🎙 ${t("recording")}` : ""),
      image: imagePreview || null,
    };
    setMessages((prev) => [...prev, userMsg]);

    setPendingImage(null);
    setPendingImageFile(null);

    // Add an empty assistant bubble immediately and track its ID
    const assistantMsgId = nextId();
    const assistantMsg = { id: assistantMsgId, role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);

    setIsLoading(true);

    sendMessageStream({
      userId: user.user_id,
      sessionId,
      text: text || undefined,
      image: image || undefined,
      audio: audio || undefined,
      onToken: (token) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: m.content + token }
              : m
          )
        );
      },
      onDone: (data) => {
        if (!sessionId) setSessionId(data.session_id);
        setAgentType(data.agent_type);
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id === assistantMsgId && data.reply) {
              return { ...m, content: data.reply };
            }
            if (m.id === userMsgId && data.transcribed_text) {
              return { ...m, content: data.transcribed_text };
            }
            return m;
          })
        );
        setIsLoading(false);
      },
      onError: (message) => {
        console.error("Stream error:", message);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: t("chat_error") }
              : m
          )
        );
        setIsLoading(false);
      },
    });
  };

  const handleSendText = (text) => {
    handleSend({
      text,
      image: pendingImageFile,
      imagePreview: pendingImage,
    });
  };

  const handleSendAudio = (audioBlob) => {
    handleSend({
      audio: audioBlob,
      image: pendingImageFile,
      imagePreview: pendingImage,
    });
  };

  const handleImageSelected = (file) => {
    setPendingImageFile(file);
    setPendingImage(URL.createObjectURL(file));
    setSheetOpen(false);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleImageSelected(file);
    e.target.value = "";
  };

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar agentType={agentType} />

      <MessageList messages={messages} isLoading={isLoading} />

      <ImagePreview
        src={pendingImage}
        onRemove={() => {
          setPendingImage(null);
          setPendingImageFile(null);
        }}
      />

      <InputBar
        onSendText={handleSendText}
        onSendAudio={handleSendAudio}
        onOpenSheet={() => setSheetOpen(true)}
        disabled={isLoading}
      />

      <ActionSheet
        visible={sheetOpen}
        onCamera={() => cameraInputRef.current?.click()}
        onGallery={() => fileInputRef.current?.click()}
        onClose={() => setSheetOpen(false)}
      />

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}
