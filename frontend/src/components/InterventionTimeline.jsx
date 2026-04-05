"use client";

/**
 * InterventionTimeline — Shows Agent node outputs in Demo Console.
 * Splits into Reflector Node and Communicator Node sections.
 */

function formatTime(ts) {
  if (!ts) return "";
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-SG", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return ts;
  }
}

function parseDecision(raw) {
  if (!raw) return null;
  try {
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch {
    return null;
  }
}

export default function InterventionTimeline({ interventions = [], polling = false }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <h2 className="text-lg font-bold mb-3">
        Agent Pipeline Output
        {polling && interventions.length === 0 && (
          <span className="text-sm font-normal text-gray-400 ml-2">
            Waiting for agent...
          </span>
        )}
      </h2>

      {interventions.length === 0 ? (
        <p className="text-sm text-gray-400">
          No interventions yet. Play a scenario to trigger the agent pipeline.
        </p>
      ) : (
        <div className="space-y-4">
          {interventions.map((iv) => {
            const isHard = iv.trigger_type?.startsWith("hard");
            const decision = parseDecision(iv.agent_decision);

            return (
              <div
                key={iv.id}
                className={`border-l-4 pl-3 py-2 ${
                  isHard
                    ? "border-red-500 bg-red-50"
                    : "border-yellow-500 bg-yellow-50"
                } rounded-r-lg`}
              >
                {/* Trigger header */}
                <div className="flex items-center gap-2 text-sm mb-2">
                  <span className="font-semibold">
                    {isHard ? "\uD83D\uDEA8" : "\u26A1"}{" "}
                    {iv.trigger_type}
                  </span>
                  <span className="text-gray-400 text-xs">
                    {formatTime(iv.triggered_at)}
                  </span>
                </div>

                {isHard ? (
                  /* Hard triggers: simple display */
                  <>
                    {iv.display_label && (
                      <p className="text-sm text-gray-600">{iv.display_label}</p>
                    )}
                  </>
                ) : (
                  /* Soft triggers: split into Reflector + Communicator */
                  <div className="space-y-3">
                    {/* Reflector Node */}
                    {decision && (
                      <div>
                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
                          Reflector Node
                        </h4>
                        <div className="bg-white/70 rounded p-2 space-y-2">
                          {/* Risk Assessment */}
                          <div>
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Risk Assessment</p>
                            <div className="flex flex-wrap gap-2 text-xs">
                              <span className={`px-1.5 py-0.5 rounded font-semibold ${
                                decision.risk_level === "HIGH" ? "bg-red-100 text-red-700" :
                                decision.risk_level === "MEDIUM" ? "bg-yellow-100 text-yellow-700" :
                                "bg-green-100 text-green-700"
                              }`}>
                                Risk: {decision.risk_level}
                              </span>
                              <span className={`px-1.5 py-0.5 rounded font-semibold ${
                                decision.intervention_action === "STRONG_ALERT" ? "bg-red-100 text-red-700" :
                                decision.intervention_action === "SOFT_REMIND" ? "bg-yellow-100 text-yellow-700" :
                                "bg-gray-100 text-gray-600"
                              }`}>
                                Action: {decision.intervention_action}
                              </span>
                              <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">
                                Confidence: {decision.confidence}
                              </span>
                            </div>
                          </div>

                          {/* Reasoning Summary */}
                          {decision.reasoning_summary && (
                            <div>
                              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Reasoning Summary</p>
                              <p className="text-xs text-gray-600 leading-relaxed">
                                {decision.reasoning_summary}
                              </p>
                            </div>
                          )}

                          {/* Supplement Recommendation */}
                          {decision.supplement_recommendation && (
                            <div>
                              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Supplement Recommendation</p>
                              <p className="text-xs text-gray-700">
                                {decision.supplement_recommendation}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Communicator Node */}
                    {iv.message_sent && (
                      <div>
                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">
                          Communicator Node
                        </h4>
                        <div className="bg-white/70 rounded p-2">
                          <p className="text-sm text-gray-700 italic leading-relaxed">
                            &quot;{iv.message_sent}&quot;
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
