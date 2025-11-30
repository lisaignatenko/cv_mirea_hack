import { useEffect } from 'react';
import styles from './App.module.css';
import Header from './components/Header/Header.jsx';
import Hero from './components/Hero/Hero.jsx';
import Highlights from './components/Highlights/Highlights.jsx';
import Workflow from './components/Workflow/Workflow.jsx';
import DashboardPreview from './components/DashboardPreview/DashboardPreview.jsx';
import ActionHistory from './components/ActionHistory/ActionHistory.jsx';
import DataCards from './components/DataCards/DataCards.jsx';
import SegmentFeed from './components/SegmentFeed/SegmentFeed.jsx';
import Footer from './components/Footer/Footer.jsx';
import { api } from './api';
import { SegmentProvider } from './context/SegmentContext.jsx';

function App() {
  useEffect(() => {
    let cancelled = false;

    const startSegmentPipeline = async () => {
      try {
        await api.startSegment();
      } catch (error) {
        if (!cancelled) {
         
          console.error('Не удалось запустить сегмент-пайплайн', error);
        }
      }
    };

    startSegmentPipeline();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <SegmentProvider>
      <div className={styles.app}>
        <Header />
        <main className={styles.main}>
          <Hero />
        <Highlights />
        <Workflow />
        <DashboardPreview />
        <ActionHistory />
        <DataCards />
        <SegmentFeed />
      </main>
        {/* <Footer /> */}
      </div>
    </SegmentProvider>
  );
}

export default App;
