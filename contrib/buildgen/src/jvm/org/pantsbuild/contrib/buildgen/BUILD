
# See go/pants for information on how to publish a new linter version.

scalac_plugin(
  name = 'emit_exported_symbols',
  plugin = 'emit-exported-symbols',
  classname = 'org.pantsbuild.contrib.buildgen.EmitExportedSymbolsPlugin',
  provides = artifact(
    org = 'org.pantsbuild.contrib.buildgen',
    name = 'emit-exported-symbols',
    repo = internal_repo,
  ),
  dependencies = [
    '3rdparty:scala-compiler-2.10.4',  # Required implicitly by plugins.
  ],
  sources = ['EmitExportedSymbolsPlugin.scala']
)

jvm_binary(
  name = 'emit_exported_symbols-binary',
  dependencies = [
    ':emit_exported_symbols',
  ],
)



# See go/pants for information on how to publish a new linter version.

scalac_plugin(
  name = 'emit_used_symbols',
  plugin = 'emit-used-symbols',
  classname = 'org.pantsbuild.contrib.buildgen.EmitUsedSymbolsPlugin',
  provides = artifact(
    org = 'org.pantsbuild.contrib.buildgen',
    name = 'emit-used-symbols',
    repo = internal_repo,
    ),
  dependencies = [
    '3rdparty:scala-compiler-2.10.4',  # Required implicitly by plugins.
  ],
  sources = ['EmitUsedSymbolsPlugin.scala']
)

jvm_binary(
  name = 'emit_used_symbols-binary',
  dependencies = [
    ':emit_used_symbols',
  ],
)
