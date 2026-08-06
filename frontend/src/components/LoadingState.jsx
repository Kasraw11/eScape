export default function LoadingState() {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-dot" aria-hidden="true" />
      Finding route alternatives and checking pedestrian data...
    </div>
  );
}
