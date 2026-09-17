"use client"

import { useState } from "react"
import OverviewPanel from "./overview-panel"
import InjuryEventScreening from "./injury-event-screening"
import RiskMatrixResult from "./risk-matrix-result"

type DashboardView = 'overview' | 'injury-screening' | 'risk-matrix'

export default function DashboardPage() {
  const [currentView, setCurrentView] = useState<DashboardView>('overview')
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null)
  const [selectedAdverseReactionId, setSelectedAdverseReactionId] = useState<number | null>(null)

  const handleNavigateToInjuryScreening = () => {
    setCurrentView('injury-screening')
  }

  const handleNavigateToRiskMatrix = (productId: number, adverseReactionId: number) => {
    setSelectedProductId(productId)
    setSelectedAdverseReactionId(adverseReactionId)
    setCurrentView('risk-matrix')
  }

  const handleBackToOverview = () => {
    setCurrentView('overview')
    setSelectedProductId(null)
    setSelectedAdverseReactionId(null)
  }

  const handleBackToInjuryScreening = () => {
    setCurrentView('injury-screening')
    setSelectedProductId(null)
    setSelectedAdverseReactionId(null)
  }

  return (
    <div className="container mx-auto px-4 pt-4 pb-8">
      {currentView === 'overview' && (
        <OverviewPanel onNavigateToInjuryScreening={handleNavigateToInjuryScreening} />
      )}
      
      {currentView === 'injury-screening' && (
        <InjuryEventScreening 
          onNavigateToRiskMatrix={handleNavigateToRiskMatrix}
          onBack={handleBackToOverview}
        />
      )}
      
      {currentView === 'risk-matrix' && selectedProductId && selectedAdverseReactionId && (
        <RiskMatrixResult 
          productId={selectedProductId}
          adverseReactionId={selectedAdverseReactionId}
          onBack={handleBackToInjuryScreening}
        />
      )}
    </div>
  )
}


