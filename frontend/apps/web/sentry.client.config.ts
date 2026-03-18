import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  // Session replay DISABLED — resume/salary data is PII (NFR-S3)
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,
  environment: process.env.NODE_ENV,
  beforeSend(event) {
    // Scrub PII fields before sending to Sentry
    if (event.request?.data) {
      const data = event.request.data as Record<string, unknown>;
      const PII_FIELDS = [
        "resume_content", "salary", "offer_amount", "ctc",
        "password", "email", "phone", "address",
      ];
      PII_FIELDS.forEach((field) => {
        if (data[field]) data[field] = "[Redacted]";
      });
    }
    return event;
  },
});
