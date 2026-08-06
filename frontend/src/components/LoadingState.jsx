export default function LoadingState() {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-spinner" aria-hidden="true" />
      <span><strong>Finding routes…</strong> Checking travel times and pedestrian-data coverage.</span>
    </div>
  );
}
