/**
 * Perspectives (ADR 0013) and Analysis are both future work - this is the
 * honest placeholder for either, not a feature dressed up as done. No
 * "Notify me" action: there is no notification system in this product to
 * back one, and a button that does nothing would be worse than no button.
 */
export function TopicStub({ title, body }: { title: string; body: string }) {
  return (
    <div className="topic-stub">
      <p className="eyebrow">{title}</p>
      <p>{body}</p>
    </div>
  );
}
