import { motion } from 'framer-motion';

export function Intelligences() {
  return (
    <div className="flex-1 flex flex-col gap-12">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-4xl md:text-5xl font-black font-headline text-white tracking-tight">Intelligences</h1>
          <p className="text-outline font-body mt-2">Aggregated Market Research & Strategic Blueprints</p>
        </motion.div>
        <div className="flex gap-3">
          <button className="px-5 py-2.5 bg-surface-container-high hover:bg-surface-bright text-white text-sm font-bold font-label transition-all">
            GENERATE SUMMARY
          </button>
          <button className="px-5 py-2.5 bg-primary-container text-primary hover:bg-primary-container/80 text-sm font-bold font-label transition-all">
            EXPORT RAW
          </button>
        </div>
      </div>

      {/* Executive Dossiers */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold font-headline text-white flex items-center gap-3">
            Executive Dossiers
            <span className="text-[10px] font-label font-medium px-2 py-0.5 border border-outline-variant/30 rounded text-outline uppercase tracking-wider">Rossini Research Dept.</span>
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Dossier Card 1 */}
          <motion.div 
            whileHover={{ y: -4 }}
            className="bg-surface-container-low p-6 rounded-lg group hover:bg-surface-container transition-all"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="p-2 bg-surface-container-lowest rounded">
                <span className="material-symbols-outlined text-tertiary">folder_managed</span>
              </div>
              <div className="flex items-center gap-2 font-label text-[10px] uppercase font-bold tracking-widest text-tertiary">
                <span className="h-1.5 w-1.5 rounded-full bg-tertiary shadow-[0_0_8px_#eac34a]"></span>
                Active
              </div>
            </div>
            <h3 className="text-xl font-headline text-white mb-2">Milan Market Penetration</h3>
            <p className="text-on-surface-variant text-sm mb-6 leading-relaxed">Analysis of competitive nightlife entities in the Navigli district. Identified three high-value acquisition targets with low digital security footprints.</p>
            <div className="flex items-center justify-between border-t border-outline-variant/10 pt-4 mt-auto">
              <span className="text-[10px] font-label text-outline uppercase">Ref: DOS-77-MIL</span>
              <a className="text-xs font-bold font-label text-primary hover:underline uppercase" href="#">View Full Report</a>
            </div>
          </motion.div>

          {/* Dossier Card 2 */}
          <motion.div 
            whileHover={{ y: -4 }}
            className="bg-surface-container-low p-6 rounded-lg group hover:bg-surface-container transition-all"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="p-2 bg-surface-container-lowest rounded">
                <span className="material-symbols-outlined text-outline">history_edu</span>
              </div>
              <div className="flex items-center gap-2 font-label text-[10px] uppercase font-bold tracking-widest text-outline">
                <span className="h-1.5 w-1.5 rounded-full bg-outline/40"></span>
                Archived
              </div>
            </div>
            <h3 className="text-xl font-headline text-white mb-2">The Roman Contingency</h3>
            <p className="text-on-surface-variant text-sm mb-6 leading-relaxed">Historical audit of the 2022 expansion into Trastevere. Core findings highlight logistic bottlenecks and local jurisdictional friction.</p>
            <div className="flex items-center justify-between border-t border-outline-variant/10 pt-4 mt-auto">
              <span className="text-[10px] font-label text-outline uppercase">Ref: DOS-22-ROM</span>
              <a className="text-xs font-bold font-label text-outline hover:underline uppercase" href="#">Review Records</a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Project Blueprints & PRDs */}
      <section>
        <h2 className="text-2xl font-bold font-headline text-white mb-6">Project Blueprints & PRDs</h2>
        <div className="bg-surface-container-lowest rounded-lg overflow-hidden border border-outline-variant/5">
          <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-surface-container-low border-b border-outline-variant/10 font-label text-[10px] uppercase font-bold tracking-widest text-outline">
            <div className="col-span-6">Document Name</div>
            <div className="col-span-3">Status</div>
            <div className="col-span-3 text-right">Last Sync</div>
          </div>
          <div className="flex flex-col">
            {/* PRD Row 1 */}
            <div className="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-surface-container transition-all group cursor-pointer border-b border-outline-variant/5">
              <div className="col-span-6 flex items-center gap-3">
                <span className="material-symbols-outlined text-primary text-lg">architecture</span>
                <span className="text-white font-medium text-sm">Vespa Surveillance Mesh (v2.1)</span>
              </div>
              <div className="col-span-3">
                <span className="px-2 py-0.5 bg-on-tertiary-fixed-variant text-tertiary text-[10px] font-label font-bold rounded uppercase">Approved</span>
              </div>
              <div className="col-span-3 text-right text-outline text-[10px] font-label">2h ago</div>
            </div>

            {/* PRD Row 2 */}
            <div className="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-surface-container transition-all group cursor-pointer border-b border-outline-variant/5">
              <div className="col-span-6 flex items-center gap-3">
                <span className="material-symbols-outlined text-outline text-lg">design_services</span>
                <span className="text-white font-medium text-sm">Automated Supply Chain Re-Routing</span>
              </div>
              <div className="col-span-3">
                <span className="px-2 py-0.5 bg-surface-container-high text-outline text-[10px] font-label font-bold rounded uppercase">Drafted</span>
              </div>
              <div className="col-span-3 text-right text-outline text-[10px] font-label">5h ago</div>
            </div>

            {/* PRD Row 3 */}
            <div className="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-surface-container transition-all group cursor-pointer">
              <div className="col-span-6 flex items-center gap-3">
                <span className="material-symbols-outlined text-primary text-lg">description</span>
                <span className="text-white font-medium text-sm">Identity Scrambler App Specs</span>
              </div>
              <div className="col-span-3">
                <span className="px-2 py-0.5 bg-on-tertiary-fixed-variant text-tertiary text-[10px] font-label font-bold rounded uppercase">Approved</span>
              </div>
              <div className="col-span-3 text-right text-outline text-[10px] font-label">12m ago</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
