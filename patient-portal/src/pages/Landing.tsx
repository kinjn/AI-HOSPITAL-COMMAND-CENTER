import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Search, ShieldCheck, Sparkles, Clock, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Sparkles,
    title: "Guided intake",
    description: "Describe how you're feeling in your own words — we'll take it from there.",
  },
  {
    icon: Clock,
    title: "Live progress",
    description: "Watch your consultation move from intake through to a care plan in real time.",
  },
  {
    icon: KeyRound,
    title: "No account needed",
    description: "You'll get a private Tracking ID at the end — that's all you need to check back in.",
  },
  {
    icon: ShieldCheck,
    title: "Private by design",
    description: "Only someone with your exact Tracking ID can ever see your consultation.",
  },
];

export default function Landing() {
  return (
    <div>
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-x-0 -top-24 h-[32rem] bg-[radial-gradient(60%_60%_at_50%_0%,hsl(var(--accent))_0%,transparent_70%)]"
          aria-hidden
        />
        <div className="relative mx-auto max-w-4xl px-4 pb-20 pt-16 text-center sm:px-6 sm:pt-24">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs font-medium text-muted-foreground shadow-soft"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-primary" />
            No account needed — just a private Tracking ID
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.05 }}
            className="font-display text-4xl font-semibold leading-tight tracking-tight text-foreground sm:text-5xl"
          >
            Care that starts the moment you need it.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1 }}
            className="mx-auto mt-5 max-w-xl text-base text-muted-foreground sm:text-lg"
          >
            Submit your symptoms and get a clear care plan. You'll receive a private Tracking ID to check your
            summary, billing estimate, and follow-up instructions any time.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.15 }}
            className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
            <Button asChild size="lg">
              <Link to="/consult/new">
                Start New Consultation <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/encounter/lookup">
                <Search /> View Existing Encounter
              </Link>
            </Button>
          </motion.div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, description }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.35, delay: i * 0.05 }}
            >
              <Card className="h-full">
                <CardContent className="p-6">
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-accent text-accent-foreground">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-4 font-display text-base font-semibold text-foreground">{title}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">{description}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="border-t border-border bg-muted/40">
        <div className="mx-auto max-w-4xl px-4 py-8 text-center text-xs text-muted-foreground sm:px-6">
          If you're experiencing a medical emergency, call your local emergency number or go to the nearest
          emergency room immediately. This portal is not intended for emergency use.
        </div>
      </section>
    </div>
  );
}
