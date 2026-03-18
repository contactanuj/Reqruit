import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  environment: process.env.NODE_ENV,
  beforeSend(event) {
    // Scrub PII fields before sending to Sentry — NFR-S3
    // Server-side errors can capture resume/salary data from request bodies
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
