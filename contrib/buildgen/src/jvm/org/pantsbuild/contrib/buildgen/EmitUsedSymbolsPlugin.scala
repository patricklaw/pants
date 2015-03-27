// Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
// Licensed under the Apache License, Version 2.0 (see LICENSE).

package org.pantsbuild.contrib.buildgen

import scala.tools.nsc.{Global, Phase}
import scala.tools.nsc.plugins.{Plugin, PluginComponent}


class EmitUsedSymbolsPlugin(val global: Global) extends Plugin {
  import global._

  val name = "emit-used-symbols"
  val description = "Emit imported or used fully qualified from source"
  val components = List[PluginComponent](EmitUsedSymbolsPluginComponent)

  private object EmitUsedSymbolsPluginComponent extends PluginComponent {
    import global._
    import global.definitions._

    val global = EmitUsedSymbolsPlugin.this.global

    override val runsAfter = List("parser")
    override val runsBefore = List("namer")

    val phaseName = EmitUsedSymbolsPlugin.this.name

    override def newPhase(prev: Phase): StdPhase = new StdPhase(prev) {
      override def name = EmitUsedSymbolsPlugin.this.name
      override def description = "Emit symbols importable from source"
      override def apply(unit: global.CompilationUnit): Unit = {
        new SymbolTraverser(unit).traverse(unit.body)
      }
    }

    val whitelistPath = System.getProperty("org.pantsbuild.contrib.buildgen.usedSymbolWhitelist")
    val outputDir = System.getProperty("org.pantsbuild.contrib.buildgen.usedSymbolOutputDir")

    val whitelist = scala.io.Source.fromFile(whitelistPath).getLines.toSet

    class SymbolTraverser(unit: CompilationUnit) extends Traverser {
      val pathSafeSource = unit.source.path.replaceAllLiterally("/", ".")
      val outputPath = outputDir + "/" + pathSafeSource

      def gatherImports(tree: Tree): Seq[String] = tree match {
        case Import(pkg, selectors) => {
          selectors.map(symbol => "%s.%s".format(pkg, symbol.name))
        }
        case _: ImplDef => List()
        case _ => {
          tree.children.flatMap(gatherImports)
        }
      }

      def gatherFQNames(tree: Tree, pid: String): Seq[String] = tree match {
        case s: Select => {
          val symbol = s.toString
          if (whitelist.contains(symbol) && (symbol != pid)) {
            List(symbol)
          } else {
            List()
          }
        }
        case Import(_, _) => List()
        case _ => {
          tree.children.flatMap(x => gatherFQNames(x, pid))
        }
      }

      override def traverse(tree: Tree): Unit = tree match {
        case PackageDef(pid, stats) => {
          val imports = gatherImports(tree).distinct
          val importsJson = imports.map(x => "\"%s\"".format(x)).mkString(",")
          val fqNames = gatherFQNames(tree, pid.toString).distinct
          val fqNamesJson = fqNames.map(x => "\"%s\"".format(x)).mkString(",")
          val outputFile = new java.io.FileWriter(outputPath)
          outputFile.write("""
            {
              "source": "%s",
              "imports": [%s],
              "fully_qualified_names": [%s]
            }
          """.format(unit.source.path, importsJson, fqNamesJson))
          outputFile.close()
        }
      }
    }
  }
}

