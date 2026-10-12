import { Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { CARE_CATEGORIES, searchCareTools } from "@/lib/care-tools";
import type { CareCategory } from "@/lib/care-tools";

export function FinderPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<CareCategory>("All");
  const results = searchCareTools(query, category);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted-foreground">Less scrolling, more growing</p>
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Search className="h-6 w-6 text-primary" aria-hidden />Find the right care tool
        </h1>
        <p className="text-sm text-muted-foreground mt-2">Search a job or symptom, then open an existing checklist. This directory does not diagnose plants or log care.</p>
      </div>
      <div className="rounded-xl border bg-card p-4 space-y-4">
        <div>
          <label htmlFor="care-search" className="text-sm font-medium">Search care tools</label>
          <input id="care-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)}
            placeholder="Try sticky, holiday, or fresh soil"
            className="mt-2 w-full rounded-lg border bg-background px-3 py-2" />
        </div>
        <div>
          <label htmlFor="care-category" className="text-sm font-medium">Category</label>
          <select id="care-category" value={category} onChange={(event) => setCategory(event.target.value as CareCategory)}
            className="mt-2 w-full rounded-lg border bg-background px-3 py-2">
            {CARE_CATEGORIES.map((item) => <option key={item}>{item}</option>)}
          </select>
        </div>
        <Button variant="outline" size="sm" onClick={() => { setQuery(""); setCategory("All"); }}>Clear filters</Button>
      </div>
      <p className="text-sm text-muted-foreground" role="status" aria-live="polite">{results.length} {results.length === 1 ? "tool" : "tools"} found</p>
      {results.length === 0 ? (
        <div className="rounded-xl border p-6">
          <h2 className="font-medium">No matching tools</h2>
          <p className="text-sm text-muted-foreground mt-1">Try a shorter search or clear the category filter.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {results.map((tool) => (
            <Link key={tool.path} to={tool.path} className="rounded-xl border bg-card p-4 transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-primary">
              <p className="text-xs text-muted-foreground">{tool.category}</p>
              <h2 className="font-semibold mt-1">{tool.title} <span aria-hidden>→</span></h2>
              <p className="text-sm text-muted-foreground mt-2">{tool.description}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
