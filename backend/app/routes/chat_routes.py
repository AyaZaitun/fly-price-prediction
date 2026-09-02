from typing import Any, Callable


def build_chat_response(
    request,
    conversation_id: str,
    trip_context: dict[str, Any],
    get_conversation: Callable,
    reply_generator: Callable,
    record_saver: Callable,
):
    memory = get_conversation(conversation_id, trip_context)
    response_text = reply_generator(memory, memory["trip_context"], request.message)
    memory["messages"].extend([
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": response_text},
    ])
    record_saver(
        conversation_id=conversation_id,
        trip_context=memory["trip_context"],
        user_message=request.message,
        assistant_response=response_text,
    )
    return {
        "conversation_id": conversation_id,
        "assistant_response": response_text,
        "trip_context": memory["trip_context"],
    }
