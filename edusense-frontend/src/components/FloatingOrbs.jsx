import React from 'react'
import { motion } from 'framer-motion'

export const FloatingOrbs = () => {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* Orb 1: Magenta Glow */}
      <motion.div
        animate={{
          x: [0, 40, -30, 0],
          y: [0, -50, 20, 0],
          scale: [1, 1.2, 0.9, 1],
        }}
        transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute -top-32 -left-32 w-96 h-96 bg-[#FF5B35]/5 rounded-full blur-3xl"
      />

      {/* Orb 2: Warm Amber Glow */}
      <motion.div
        animate={{
          x: [0, -60, 40, 0],
          y: [0, 40, -30, 0],
          scale: [1, 0.9, 1.15, 1],
        }}
        transition={{ duration: 22, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute top-1/3 -right-32 w-[30rem] h-[30rem] bg-[#F59E0B]/5 rounded-full blur-3xl"
      />

      {/* Orb 3: Subtle Sky Accent */}
      <motion.div
        animate={{
          x: [0, 30, -50, 0],
          y: [0, 30, 40, 0],
          scale: [1, 1.1, 0.85, 1],
        }}
        transition={{ duration: 25, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute -bottom-32 left-1/4 w-80 h-80 bg-orange-100/40 rounded-full blur-3xl"
      />
    </div>
  )
}
