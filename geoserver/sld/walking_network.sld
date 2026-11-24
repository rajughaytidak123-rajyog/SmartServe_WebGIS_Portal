<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc" 
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>walking_network</Name>
    <UserStyle>
      <Title>PMC Pedestrian Walking Network Style</Title>
      <Abstract>Subtle network lines scaled by hierarchy</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <Name>WalkableStreet</Name>
          <Title>Walkable Street</Title>
          <LineSymbolizer>
            <Stroke>
              <CssParameter name="stroke">#64748b</CssParameter>
              <CssParameter name="stroke-width">0.8</CssParameter>
              <CssParameter name="stroke-opacity">0.6</CssParameter>
            </Stroke>
          </LineSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
