import ReactMarkdown from "react-markdown";

export default function MessageBubble({ role, content, image }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-4`}>
      <div
        className={`max-w-[70%] px-4 py-3 ${
          isUser
            ? "bg-bubble-user rounded-[36px] rounded-br-lg"
            : "bg-bubble-ai rounded-[35px] rounded-bl-lg"
        }`}
      >
        {image && (
          <img
            src={image}
            alt="uploaded"
            className="w-full rounded-2xl mb-2 max-h-48 object-cover"
          />
        )}
        {!isUser && !content ? (
          <div className="flex gap-1 py-0.5">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.15s]" />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.3s]" />
          </div>
        ) : content ? (
          isUser ? (
            <p className="text-sm leading-relaxed">{content}</p>
          ) : (
            <div className="text-sm leading-relaxed prose prose-sm max-w-none
              prose-p:my-1 prose-ul:my-1 prose-li:my-0.5
              prose-ul:pl-4 prose-li:leading-relaxed">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )
        ) : null}
      </div>
    </div>
  );
}
