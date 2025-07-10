# 3D Models Directory

This directory contains glTF models for unit visualization in the advanced 3D Cesium view.

## Required Models

- `aircraft.glb` - Aircraft/plane models
- `ship.glb` - Naval vessel models  
- `tank.glb` - Ground vehicle/tank models
- `generic.glb` - Generic unit fallback model

## Model Requirements

- Format: glTF 2.0 (.glb binary format preferred)
- Scale: Models should be appropriately sized for their unit type
- Orientation: Forward direction should be positive Y-axis
- Textures: Embedded in glTF file
- LOD: Consider multiple levels of detail for performance

## Local Asset Pipeline (Future Implementation)

1. **Terrain**: Convert elevation data to quantized-mesh tiles
2. **Buildings**: Convert OSM/LiDAR data to 3D Tiles format
3. **Models**: Optimize glTF models for real-time rendering
4. **Hosting**: Serve all assets from local NGINX server

## Current Status

- Using fallback models and external terrain/building services
- Ready for local asset integration when available