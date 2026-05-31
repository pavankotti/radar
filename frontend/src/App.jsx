import React, { useState, useEffect } from 'react';
import { Search, MapPin, Globe, Briefcase, Terminal } from 'lucide-react';

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    is_remote: false,
    is_new_grad: false,
    visa_sponsorship: false
  });
  const [isLoading, setIsLoading] = useState(true);

  // Debounced search effect
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchJobs();
    }, 300); // Wait 300ms after user stops typing before hitting API

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery, filters]);

  const fetchJobs = () => {
    // Build dynamic query params from state
    const params = new URLSearchParams({ limit: '100' });
    if (searchQuery.trim()) params.append('q', searchQuery);
    if (filters.is_remote) params.append('is_remote', 'true');
    if (filters.is_new_grad) params.append('is_new_grad', 'true');
    if (filters.visa_sponsorship) params.append('visa_sponsorship', 'true');

    setIsLoading(true);
    fetch(`http://localhost:8000/api/v1/jobs/?${params.toString()}`)
      .then(res => res.json())
      .then(data => {
        setJobs(data.jobs || []);
        setIsLoading(false);
      })
      .catch(err => {
        console.error(err);
        setIsLoading(false);
      });
  };

  const toggleFilter = (key) => {
    setFilters(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="min-h-screen bg-background text-text-primary flex flex-col font-sans selection:bg-accent selection:text-black">
      {/* Ultra Clean Top Navbar */}
      <nav className="flex items-center px-8 py-5 border-b border-surface/50 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <Terminal className="text-accent w-7 h-7" />
          <span className="text-xl font-bold tracking-tight">Radar.</span>
        </div>
      </nav>

      {/* Main Search Area */}
      <main className="flex-1 overflow-y-auto p-8 max-w-7xl mx-auto w-full">
        <div className="mb-12 flex flex-col items-center text-center mt-6">
          <h1 className="text-5xl font-bold mb-4 tracking-tight">Discover Elite Engineering Roles</h1>
          <p className="text-text-secondary mb-10 text-lg max-w-xl">
            Our intelligence engine curates deduplicated software positions actively hiring across the world.
          </p>
          
          {/* Centralized Search Bar */}
          <div className="relative w-full max-w-3xl mb-6">
            <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-6 h-6 text-text-secondary" />
            <input 
              type="text" 
              placeholder="Search by title, tech stack, or company (e.g. 'Kubernetes' or 'Stripe')..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface border border-surface-hover rounded-full pl-16 pr-8 py-4 outline-none text-lg placeholder:text-text-secondary focus:border-accent/50 focus:ring-2 focus:ring-accent/20 transition-all shadow-lg"
            />
          </div>

          {/* Functional Query Filter Pills */}
          <div className="flex flex-wrap items-center justify-center gap-4">
            <button 
              onClick={() => toggleFilter('is_remote')}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-full border transition-all font-medium ${filters.is_remote ? 'bg-accent/10 border-accent/50 text-accent shadow-[0_0_15px_rgba(204,255,0,0.2)]' : 'bg-surface border-surface-hover text-text-secondary hover:text-white hover:border-text-secondary/30'}`}
            >
              <Globe className="w-4 h-4" /> Fully Remote
            </button>
            <button 
              onClick={() => toggleFilter('is_new_grad')}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-full border transition-all font-medium ${filters.is_new_grad ? 'bg-purple-500/10 border-purple-500/50 text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.2)]' : 'bg-surface border-surface-hover text-text-secondary hover:text-white hover:border-text-secondary/30'}`}
            >
              <Briefcase className="w-4 h-4" /> New Grad (0-2 YOE)
            </button>
            <button 
              onClick={() => toggleFilter('visa_sponsorship')}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-full border transition-all font-medium ${filters.visa_sponsorship ? 'bg-blue-500/10 border-blue-500/50 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.2)]' : 'bg-surface border-surface-hover text-text-secondary hover:text-white hover:border-text-secondary/30'}`}
            >
              <MapPin className="w-4 h-4" /> Visa Sponsorship
            </button>
          </div>
        </div>

        {/* Results Grid Area */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading ? (
            <div className="col-span-full flex items-center justify-center p-20 text-text-secondary">
              <div className="flex flex-col items-center gap-4">
                <div className="w-10 h-10 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>
                <p className="text-lg">Querying Engine Database...</p>
              </div>
            </div>
          ) : jobs.length === 0 ? (
            <div className="col-span-full flex flex-col items-center justify-center p-20 text-text-secondary bg-surface/30 rounded-3xl border border-surface-hover border-dashed">
              <Terminal className="w-12 h-12 mb-4 text-surface-hover" />
              <h3 className="text-xl text-white font-semibold mb-2">No Matches Found</h3>
              <p>Try adjusting your search filters or clearing the text query.</p>
            </div>
          ) : (
            jobs.map(job => (
              <a 
                key={job.id} 
                href={job.canonical_url || job.source_url} 
                target="_blank" 
                rel="noreferrer"
                className="bg-surface rounded-2xl p-6 border border-surface-hover hover:border-accent/50 transition-all duration-300 flex flex-col group cursor-pointer hover:-translate-y-1 hover:shadow-[0_10px_40px_rgba(204,255,0,0.08)]"
              >
                <div className="flex justify-between items-start mb-5">
                  <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center text-black font-black text-xl uppercase shadow-sm">
                    {job.company_name.charAt(0)}
                  </div>
                  <span className="text-xs font-medium text-text-secondary bg-background px-3 py-1.5 rounded-full border border-surface-hover flex items-center gap-1 group-hover:border-accent/30 transition-colors">
                    {new Date(job.published_at || job.scraped_at).toLocaleDateString()}
                  </span>
                </div>
                
                <h3 className="text-xl font-bold mb-2 group-hover:text-accent transition-colors line-clamp-2">{job.title}</h3>
                <p className="text-text-secondary text-sm mb-6 line-clamp-2 leading-relaxed">
                  Join <strong className="text-white font-semibold">{job.company_name}</strong> as a {job.title}. This role is actively hiring and matched your specialized criteria.
                </p>
                
                <div className="mt-auto flex flex-wrap gap-2 pt-5 border-t border-surface-hover/70 group-hover:border-accent/20 transition-colors">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-wide uppercase bg-background px-3 py-1.5 rounded-md border border-surface-hover text-text-secondary">
                    <MapPin className="w-3.5 h-3.5" />
                    {job.location.split(',')[0]}
                  </div>
                  {job.is_remote && (
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-wide uppercase bg-accent/5 px-3 py-1.5 rounded-md border border-accent/20 text-accent">
                      <Globe className="w-3.5 h-3.5" /> Remote
                    </div>
                  )}
                  {job.is_new_grad && (
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-wide uppercase bg-purple-500/5 px-3 py-1.5 rounded-md border border-purple-500/20 text-purple-400">
                      <Briefcase className="w-3.5 h-3.5" /> Entry
                    </div>
                  )}
                </div>
              </a>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
