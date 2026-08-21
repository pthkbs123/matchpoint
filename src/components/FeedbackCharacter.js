function FeedbackCharacter({ type }) {
  if (type === 'cavity_alert') {
    return (
      <div className="feedback-character monster" aria-hidden="true">
        <svg viewBox="0 0 150 126">
          <path className="monster-horn" d="M38 37 24 11l30 13M112 37l14-26-30 13" />
          <path className="monster-body" d="M29 67c0-30 19-48 46-48s46 18 46 48c0 26-18 45-46 45S29 93 29 67Z" />
          <circle className="monster-eye" cx="57" cy="62" r="8" />
          <circle className="monster-eye" cx="93" cy="62" r="8" />
          <circle className="monster-pupil" cx="59" cy="64" r="3" />
          <circle className="monster-pupil" cx="91" cy="64" r="3" />
          <path className="monster-mouth" d="M54 88c12 9 30 9 42 0" />
          <path className="monster-tooth" d="m67 87 8 14 8-14" />
          <path className="monster-arm" d="M32 75 12 89M118 75l20 14" />
        </svg>
      </div>
    );
  }

  if (type === 'capture_retry' || type === 'analysis_error') {
    return (
      <div className="feedback-character retry" aria-hidden="true">
        <svg viewBox="0 0 150 126">
          <path className="tooth-body" d="M47 20c11 0 17 6 28 6s17-6 28-6c20 0 29 15 25 34-3 14-12 19-14 36-2 17-7 26-16 26-11 0-11-24-23-24s-12 24-23 24c-9 0-14-9-16-26-2-17-11-22-14-36-4-19 5-34 25-34Z" />
          <path className="retry-arrow" d="M47 64a30 30 0 0 1 51-19l7 7M104 35v17H87M103 65a30 30 0 0 1-51 19l-7-7M46 94V77h17" />
        </svg>
      </div>
    );
  }

  return (
    <div className="feedback-character healthy" aria-hidden="true">
      <svg viewBox="0 0 150 126">
        <path className="tooth-body" d="M47 20c11 0 17 6 28 6s17-6 28-6c20 0 29 15 25 34-3 14-12 19-14 36-2 17-7 26-16 26-11 0-11-24-23-24s-12 24-23 24c-9 0-14-9-16-26-2-17-11-22-14-36-4-19 5-34 25-34Z" />
        <circle className="tooth-eye" cx="58" cy="61" r="4" />
        <circle className="tooth-eye" cx="92" cy="61" r="4" />
        <path className="tooth-smile" d="M58 77c9 10 25 10 34 0" />
        <path className="tooth-sparkle" d="m123 18 3 8 8 3-8 3-3 8-3-8-8-3 8-3Z" />
      </svg>
    </div>
  );
}

export default FeedbackCharacter;
